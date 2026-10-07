from typing import Dict, Any, List
from src.guardian.engine.rules import load_guardian_config, compute_combined_risk, evaluate_hard_rules
from src.guardian.engine.narrator import generate_customer_message, generate_analyst_narrative
from src.guardian.engine.guard import sanitize_input_text

LEVEL_RANK = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}
RANK_TO_LEVEL = {0: "L0", 1: "L1", 2: "L2", 3: "L3", 4: "L4"}


class DecisionEngine:
    def __init__(self, config_path: str = "config/guardian.yaml"):
        self.config = load_guardian_config(config_path)
        self.ladder_cfg = self.config["friction_ladder"]["levels"]
        self.weights = self.config["risk_weights"]
        self.vuln_cfg = self.config["vulnerability_policy"]

    def decide(
        self,
        transaction_context: Dict[str, Any],
        raw_message_text: str = "",
        txn_ml_score: float = 0.0,
        text_scam_score: float = 0.0,
        graph_risk: float = 0.0,
        anomaly_score: float = 0.0,
        shap_reasons: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Coordinates full decisioning: Sanitization -> Risk Combination -> 
        Vulnerability Calibration -> Hard Rule Evaluation -> Ladder Assignment.
        """
        shap_reasons = shap_reasons or []

        # 1. Sanitize text input against prompt injection
        cleaned_text, injection_detected = sanitize_input_text(
            raw_message_text)

        # 2. Compute composite weighted risk
        composite_risk = compute_combined_risk(
            txn_ml_score=txn_ml_score,
            text_scam_score=text_scam_score,
            graph_risk=graph_risk,
            anomaly_score=anomaly_score,
            weights=self.weights
        )

        # 3. Dynamic Threshold Adjustment for Vulnerable Cohorts
        user_vuln = transaction_context.get("vulnerability_score", 0.20)
        is_vulnerable = user_vuln >= self.vuln_cfg["high_vulnerability_threshold"]
        discount = self.vuln_cfg["threshold_discount_factor"] if is_vulnerable else 0.0

        # Calculate base level from score thresholds
        assigned_level = "L0"
        if composite_risk >= (self.ladder_cfg["L4"]["threshold"] - discount):
            assigned_level = "L4"
        elif composite_risk >= (self.ladder_cfg["L3"]["threshold"] - discount):
            assigned_level = "L3"
        elif composite_risk >= (self.ladder_cfg["L2"]["threshold"] - discount):
            assigned_level = "L2"
        elif composite_risk >= (self.ladder_cfg["L1"]["threshold"] - discount):
            assigned_level = "L1"

        # 4. Check Hard Rule Overrides
        rule_level, rule_traces = evaluate_hard_rules(
            transaction_context, self.config)

        if injection_detected:
            rule_traces.append(
                "SECURITY_GUARD: Adversarial prompt injection detected and neutralized.")
            # Automatically escalate prompt injection attacks to at least L2 Cool-off Hold
            if LEVEL_RANK[rule_level] < LEVEL_RANK["L2"]:
                rule_level = "L2"

        # Enforce maximum of (assigned_level, rule_level)
        final_level = RANK_TO_LEVEL[max(
            LEVEL_RANK[assigned_level], LEVEL_RANK[rule_level])]

        # If L3 is selected but user has no trusted contact registered, gracefully route to L2 + Informative
        if final_level == "L3" and not transaction_context.get("has_trusted_contact", True):
            final_level = "L2"
            rule_traces.append(
                "FALLBACK_NO_TRUSTED_CONTACT: User has no registered contact; adjusted to L2.")

        # 5. Extract reason codes
        reason_codes = [r["reason_code"]
                        for r in shap_reasons if "reason_code" in r]
        if not reason_codes and final_level != "L0":
            if graph_risk > 0.6:
                reason_codes.append("MULE_NETWORK_SUSPECT")
            elif transaction_context.get("is_new_device", 0) == 1:
                reason_codes.append("NEW_DEVICE_SPIKE")

        # 6. Generate bilingual plain explanations & analyst narratives
        customer_bn, customer_en = generate_customer_message(
            final_level, reason_codes, self.config)
        narrative = generate_analyst_narrative(
            context=transaction_context,
            risk_score=composite_risk,
            level=final_level,
            reasons=shap_reasons,
            rules_triggered=rule_traces
        )

        return {
            "action_level": final_level,
            "risk_score": composite_risk,
            "is_vulnerable_user": is_vulnerable,
            "reason_codes": reason_codes,
            "rule_trace": rule_traces,
            "customer_message_bn": customer_bn,
            "customer_message_en": customer_en,
            "analyst_narrative": narrative,
            "evidence": {
                "txn_ml_score": txn_ml_score,
                "text_scam_score": text_scam_score,
                "graph_risk": graph_risk,
                "anomaly_score": anomaly_score,
                "injection_detected": injection_detected
            }
        }
