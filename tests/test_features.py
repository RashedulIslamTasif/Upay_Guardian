import pytest
import pandas as pd
import numpy as np
from src.guardian.datagen.users import generate_users, generate_agents
from src.guardian.datagen.scam_texts import generate_scam_corpus
from src.guardian.datagen.transactions import generate_transactions
from src.guardian.features.behavior import extract_behavioral_features
from src.guardian.features.graph import build_transaction_graph, attach_graph_features, export_subgraph_json
from src.guardian.features.text import clean_text, extract_keyword_salience

def test_feature_engineering_pipeline():
    users = generate_users(n_users=50, seed=42)
    agents = generate_agents(n_agents=10, seed=42)
    train_texts, test_texts = generate_scam_corpus(n_samples=50, seed=42)
    txns = generate_transactions(users, agents, pd.concat([train_texts, test_texts]), n_txns=300, seed=42)
    
    feat_df = extract_behavioral_features(txns, users)
    
    assert "amount_ratio_to_baseline" in feat_df.columns
    assert "is_new_device" in feat_df.columns
    assert "is_new_recipient" in feat_df.columns
    assert "velocity_count_1h" in feat_df.columns
    assert feat_df["velocity_count_1h"].min() >= 0
    assert not feat_df["amount_ratio_to_baseline"].isna().any()

def test_graph_intelligence_and_mule_proximity():
    users = generate_users(n_users=30, seed=42)
    agents = generate_agents(n_agents=5, seed=42)
    # Ensure one agent is flagged as mule
    agents.loc[0, "is_flagged_mule_cluster"] = True
    flagged_id = agents.loc[0, "entity_id"]
    
    train_texts, test_texts = generate_scam_corpus(n_samples=20, seed=42)
    txns = generate_transactions(users, agents, pd.concat([train_texts, test_texts]), n_txns=100, seed=42)
    
    G, risk_map = build_transaction_graph(txns, agents)
    assert flagged_id in risk_map
    assert risk_map[flagged_id] >= 0.90 # Flagged entity gets near-maximum risk
    
    df_with_graph = attach_graph_features(txns, risk_map)
    assert "recipient_graph_risk" in df_with_graph.columns
    
    json_graph = export_subgraph_json(G, risk_map, max_nodes=10)
    assert "nodes" in json_graph and "edges" in json_graph

def test_text_cleaning_and_salience():
    raw_bengali = "আপনার OTP কোড 123456 কারো সাথে শেয়ার করবেন না!"
    salience = extract_keyword_salience(raw_bengali)
    assert salience["has_high_urgency_keyword"] is True
    assert "otp" in salience["matched_keywords"] or "ওটিপি" in salience["matched_keywords"]