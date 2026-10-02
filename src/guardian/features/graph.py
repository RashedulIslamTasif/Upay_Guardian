import json
import networkx as nx
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

def build_transaction_graph(
    txns_df: pd.DataFrame,
    agents_df: pd.DataFrame
) -> Tuple[nx.DiGraph, Dict[str, float]]:
    """Build directed entity graph and compute network topology risk metrics."""
    G = nx.DiGraph()
    
    flagged_entities = set(agents_df[agents_df["is_flagged_mule_cluster"]]["entity_id"].values)
    
    # Aggregate transaction edges
    edge_summary = txns_df.groupby(["user_id", "recipient_id"]).agg(
        weight=("amount", "sum"),
        txn_count=("txn_id", "count")
    ).reset_index()
    
    for _, row in edge_summary.iterrows():
        G.add_edge(
            str(row["user_id"]),
            str(row["recipient_id"]),
            weight=float(row["weight"]),
            count=int(row["txn_count"])
        )
        
    in_degrees = dict(G.in_degree())
    out_degrees = dict(G.out_degree())
    
    graph_risk = {}
    for node in G.nodes():
        risk = 0.05
        # High fan-in (many victims sending to one entity) is indicative of mule/scammer aggregation
        in_deg = in_degrees.get(node, 0)
        out_deg = out_degrees.get(node, 0)
        
        if in_deg >= 5:
            risk += min(0.40, (in_deg - 4) * 0.05)
        if in_deg >= 3 and out_deg >= 2: # Pass-through aggregator
            risk += 0.25
            
        # Flagged node proximity check (1 or 2 hops from confirmed mule cluster)
        if node in flagged_entities:
            risk = 0.98
        else:
            for flagged in flagged_entities:
                if G.has_node(flagged):
                    if nx.has_path(G, node, flagged):
                        try:
                            dist = nx.shortest_path_length(G, node, flagged)
                            if dist == 1:
                                risk = max(risk, 0.85)
                            elif dist == 2:
                                risk = max(risk, 0.55)
                        except nx.NetworkXNoPath:
                            pass
        graph_risk[node] = float(np.clip(risk, 0.01, 0.99))
        
    return G, graph_risk

def attach_graph_features(
    txns_df: pd.DataFrame,
    graph_risk: Dict[str, float]
) -> pd.DataFrame:
    df = txns_df.copy()
    df["recipient_graph_risk"] = df["recipient_id"].map(graph_risk).fillna(0.05)
    return df

def export_subgraph_json(
    G: nx.DiGraph,
    graph_risk: Dict[str, float],
    center_node: str = None,
    max_nodes: int = 40
) -> str:
    """Export lightweight JSON subgraph formatted for UI visualization."""
    if center_node and G.has_node(center_node):
        neighbors = set([center_node])
        neighbors.update(G.successors(center_node))
        neighbors.update(G.predecessors(center_node))
        sub_nodes = list(neighbors)[:max_nodes]
    else:
        # Fallback to top high-risk nodes
        sorted_nodes = sorted(graph_risk.items(), key=lambda x: x[1], reverse=True)
        sub_nodes = [n for n, _ in sorted_nodes[:max_nodes] if G.has_node(n)]
        
    subG = G.subgraph(sub_nodes)
    
    nodes_data = [
        {"id": n, "label": n, "risk": round(graph_risk.get(n, 0.05), 2)}
        for n in subG.nodes()
    ]
    edges_data = [
        {"source": u, "target": v, "weight": d.get("weight", 1.0)}
        for u, v, d in subG.edges(data=True)
    ]
    return json.dumps({"nodes": nodes_data, "edges": edges_data}, indent=2)