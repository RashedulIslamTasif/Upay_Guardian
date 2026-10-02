import os
import json
import argparse
import pandas as pd
import numpy as np

from src.guardian.models.text_clf import ScamTextClassifier
from src.guardian.models.txn_model import TransactionRiskModel
from src.guardian.models.anomaly import BehavioralAnomalyDetector
from src.guardian.models.explain import ModelExplainer
from src.guardian.engine.ladder import DecisionEngine
from src.guardian.eval.metrics import evaluate_model_performance, evaluate_text_unseen_split
from src.guardian.eval.simulate_ab import simulate_business_outcomes, generate_tradeoff_curve
from src.guardian.eval.fairness import evaluate_demographic_fairness

def run_evaluation(data_dir: str = "data", artifacts_dir: str = "models_artifacts", output_json: str = "data/eval_results.json"):
    print("==========================================================")
    print(" [Guardian] Running Comprehensive Evaluation Suite ")
    print("==========================================================")

    # 1. Load models & clean held-out test data
    print("[-] Loading test artifacts and held-out test transactions...")
    test_df = pd.read_parquet(os.path.join(data_dir, "held_out_test_txns.parquet"))
    test_texts = pd.read_parquet(os.path.join(data_dir, "scam_texts_test.parquet"))
    
    # Ensure demographic attributes exist for fairness slicing
    users_path = os.path.join(data_dir, "users.parquet")
    if os.path.exists(users_path):
        users_df = pd.read_parquet(users_path)
        missing_demographics = [c for c in ["age_group", "region", "tenure_days"] if c not in test_df.columns]
        if missing_demographics:
            test_df = test_df.merge(users_df[["user_id"] + missing_demographics], on="user_id", how="left")

    text_clf = ScamTextClassifier.load(os.path.join(artifacts_dir, "text_clf.joblib"))
    txn_model = TransactionRiskModel.load(os.path.join(artifacts_dir, "txn_model.joblib"))
    anomaly_model = BehavioralAnomalyDetector.load(os.path.join(artifacts_dir, "anomaly_model.joblib"))
    engine = DecisionEngine()

    # 2. ML Performance Metrics
    print("[-] Computing ML model performance on held-out test...")
    y_probs = txn_model.predict_risk(test_df)
    ml_perf = evaluate_model_performance(test_df["label_scam"].values, y_probs)

    print("[-] Evaluating NLP classifier on unseen template families...")
    text_perf = evaluate_text_unseen_split(test_texts, text_clf)

    # 3. Simulate Rule-Only Baseline vs. Full Guardian Engine
    print("[-] Executing Guardian Decision Engine over test horizon...")
    anomaly_scores = anomaly_model.score(test_df)
    assigned_levels = []
    baseline_rule_levels = []

    for i in range(len(test_df)):
        row = test_df.iloc[i].to_dict()
        prob = float(y_probs[i])
        anom = float(anomaly_scores[i])
        gr = float(row.get("recipient_graph_risk", 0.05))

        # Full AI Guardian
        res = engine.decide(row, txn_ml_score=prob, text_scam_score=0.1, graph_risk=gr, anomaly_score=anom)
        assigned_levels.append(res["action_level"])

        # Simple deterministic rule baseline (amount > 5000 and new recipient)
        if row.get("amount", 0) > 5000 and row.get("is_new_recipient", 0) == 1:
            baseline_rule_levels.append("L2")
        else:
            baseline_rule_levels.append("L0")

    # 4. Business Simulation
    print("[-] Simulating counterfactual economic impact (Control vs Guardian)...")
    treatment_impact = simulate_business_outcomes(test_df, assigned_levels)
    baseline_impact = simulate_business_outcomes(test_df, baseline_rule_levels)
    tradeoff_curve = generate_tradeoff_curve(test_df, y_probs)

    # 5. Fairness & Parity Audits
    print("[-] Conducting demographic parity & fairness audits...")
    fairness_report = evaluate_demographic_fairness(test_df, assigned_levels)

    # Assemble comprehensive results package
    results = {
        "model_performance": ml_perf,
        "nlp_unseen_performance": {
            "macro_f1": text_perf["unseen_template_macro_f1"],
            "classes": text_perf["classes"]
        },
        "business_simulation": {
            "guardian_treatment": treatment_impact,
            "rule_only_baseline": baseline_impact,
            "ai_uplift_loss_prevented_bdt": round(
                treatment_impact["prevented_loss_bdt"] - baseline_impact["prevented_loss_bdt"], 2
            ),
            "tradeoff_curve": tradeoff_curve
        },
        "fairness_audit": fairness_report
    }

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n=================== EVALUATION RESULTS ===================")
    print(f" LightGBM PR-AUC:                 {ml_perf['pr_auc']:.4f}")
    print(f" Recall @ Top 2% Capacity:        {ml_perf['recall_at_2_percent_capacity']*100:.1f}%")
    print(f" Unseen NLP Macro-F1:             {text_perf['unseen_template_macro_f1']:.4f}")
    print(f" Scam Loss Prevented:             ৳{treatment_impact['prevented_loss_bdt']:,.2f} ({treatment_impact['loss_reduction_pct']}%)")
    print(f" AI Value Add Over Simple Rules:  ৳{results['business_simulation']['ai_uplift_loss_prevented_bdt']:,.2f}")
    print(f" Legitimate User Friction Rate:   {treatment_impact['legit_friction_rate_pct']}%")
    print(f" Analyst Hours Saved (Narratives):{treatment_impact['analyst_hours_saved']} hrs")
    print(f" Saved Audit JSON to:             {output_json}")
    print("==========================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="data")
    parser.add_argument("--artifacts_dir", type=str, default="models_artifacts")
    parser.add_argument("--output_json", type=str, default="data/eval_results.json")
    args = parser.parse_args()

    run_evaluation(args.data_dir, args.artifacts_dir, args.output_json)