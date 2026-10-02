import os
import argparse
import pandas as pd
import numpy as np
from src.guardian.features.behavior import extract_behavioral_features
from src.guardian.features.graph import build_transaction_graph, attach_graph_features
from src.guardian.models.text_clf import ScamTextClassifier
from src.guardian.models.txn_model import TransactionRiskModel
from src.guardian.models.anomaly import BehavioralAnomalyDetector
from src.guardian.models.explain import ModelExplainer

def train_all(data_dir: str = "data", artifacts_dir: str = "models_artifacts"):
    print("==========================================================")
    print(" [Guardian] Training Multi-Modal Detection Models")
    print("==========================================================")
    os.makedirs(artifacts_dir, exist_ok=True)

    # 1. Train Multilingual Scam NLP Classifier (Unseen template split)
    print("[-] Training TF-IDF char n-gram Scam Text Classifier...")
    train_texts = pd.read_parquet(os.path.join(data_dir, "scam_texts_train.parquet"))
    text_clf = ScamTextClassifier()
    text_clf.fit(train_texts["text"].tolist(), train_texts["category"].tolist())
    text_clf.save(os.path.join(artifacts_dir, "text_clf.joblib"))
    print("    [✓] Text Classifier trained and saved.")

    # 2. Load & Prepare Tabular Transaction Features
    print("[-] Ingesting users, agents, and time-sequenced transactions...")
    users_df = pd.read_parquet(os.path.join(data_dir, "users.parquet"))
    agents_df = pd.read_parquet(os.path.join(data_dir, "agents.parquet"))
    txns_df = pd.read_parquet(os.path.join(data_dir, "transactions.parquet"))

    print("[-] Computing NetworkX transaction graph topology risks...")
    G, graph_risk = build_transaction_graph(txns_df, agents_df)
    txns_df = attach_graph_features(txns_df, graph_risk)

    print("[-] Extracting rolling behavioral & temporal features...")
    txns_feat = extract_behavioral_features(txns_df, users_df)

    # 3. Train Behavioral Anomaly Isolation Forest
    print("[-] Training Behavioral Anomaly Isolation Forest...")
    anomaly_model = BehavioralAnomalyDetector()
    # Train anomaly detector strictly on normal transactions
    normal_subset = txns_feat[txns_feat["label_scam"] == 0]
    anomaly_model.fit(normal_subset)
    anomaly_model.save(os.path.join(artifacts_dir, "anomaly_model.joblib"))
    print("    [✓] Anomaly Detector trained and saved.")

    # 4. Time-Based Train / Validation / Test Split (Strict Leakage Prevention)
    print("[-] Performing chronological split (70% Train, 15% Val, 15% Test)...")
    txns_feat = txns_feat.sort_values("timestamp").reset_index(drop=True)
    n = len(txns_feat)
    train_idx = int(n * 0.70)
    val_idx = int(n * 0.85)

    df_train = txns_feat.iloc[:train_idx]
    df_val = txns_feat.iloc[train_idx:val_idx]
    df_test = txns_feat.iloc[val_idx:]

    # Save clean held-out test split for Phase 5 business evaluation
    df_test.to_parquet(os.path.join(data_dir, "held_out_test_txns.parquet"), index=False)

    # 5. Train & Calibrate LightGBM Transaction Model
    print("[-] Training and Platt-calibrating LightGBM Transaction Model...")
    txn_model = TransactionRiskModel()
    txn_model.fit(
        X_train=df_train,
        y_train=df_train["label_scam"],
        X_val=df_val,
        y_val=df_val["label_scam"]
    )
    txn_model.save(os.path.join(artifacts_dir, "txn_model.joblib"))
    print("    [✓] Calibrated LightGBM Model saved.")

    # 6. Fit & Save SHAP TreeExplainer
    print("[-] Initializing SHAP TreeExplainer for real-time attribution...")
    explainer = ModelExplainer(txn_model.model, txn_model.feature_columns)
    explainer.save(os.path.join(artifacts_dir, "explainer.joblib"))
    print("    [✓] SHAP Explainer saved.")

    print(f"[✓] All models successfully saved to '{artifacts_dir}/'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="data")
    parser.add_argument("--artifacts_dir", type=str, default="models_artifacts")
    args = parser.parse_args()
    train_all(args.data_dir, args.artifacts_dir)