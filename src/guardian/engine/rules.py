import yaml
import os
from typing import Dict, Any, List, Tuple

DEFAULT_CONFIG_PATH = os.path.join("config", "guardian.yaml")

def load_guardian_config(path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def compute_combined_risk(
    txn_ml_score: float,
    text_scam_score: float,
    graph_risk: float,
    anomaly_score: float,
    weights: Dict[str, float]
) -> float:
    """Computes weighted multi-modal risk score."""
    total_score = (
        (txn_ml_score * weights.get("txn_ml_score", 0.40)) +
        (text_scam_score * weights.get("text_scam_score", 0.30)) +
        (graph_risk * weights.get("graph_risk_score", 0.15)) +
        (anomaly_score * weights.get("behavior_anomaly_score", 0.15))
    )
    return round(float(total_score), 4)

def evaluate_hard_rules(
    context: Dict[str, Any],
    config: Dict[str, Any]
) -> Tuple[str, List[str]]:
    """
    Evaluates deterministic override rules defined in config.
    Returns: (enforced_minimum_level, triggered_rule_traces)
    """
    enforced_level = "L0"
    traces = []
    
    text_class = context.get("text_scam_type", "benign")
    is_new_recipient = context.get("is_new_recipient", False)
    graph_risk = context.get("recipient_graph_risk", 0.0)
    amount_ratio = context.get("amount_ratio_to_baseline", 1.0)
    
    # 1. OTP Phishing + New Beneficiary -> Forces minimum L2
    if text_class == "otp_pin_request" and is_new_recipient:
        enforced_level = "L2"
        traces.append("RULE_OTP_DRAIN: OTP request accompanied by new recipient transfer.")
        
    # 2. Confirmed Mule Cluster Link + Large Amount -> Forces minimum L3
    if graph_risk >= 0.85 and amount_ratio >= 3.0:
        enforced_level = "L3"
        traces.append("RULE_MULE_HOP: Recipient is high-confidence mule node with large outflow.")
        
    # 3. Sent by mistake refund pattern
    if text_class == "sent_by_mistake" and amount_ratio >= 2.0:
        if enforced_level in ["L0", "L1"]:
            enforced_level = "L2"
        traces.append("RULE_MISTAKE_REFUND: Outbound transfer triggered by mistaken send message.")
        
    return enforced_level, traces