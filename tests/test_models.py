import os
import pytest
import pandas as pd
import numpy as np
from src.guardian.datagen.scam_texts import generate_scam_corpus
from src.guardian.datagen.users import generate_users, generate_agents
from src.guardian.datagen.transactions import generate_transactions
from src.guardian.features.behavior import extract_behavioral_features
from src.guardian.features.graph import build_transaction_graph, attach_graph_features
from src.guardian.models.text_clf import ScamTextClassifier
from src.guardian.models.txn_model import TransactionRiskModel
from src.guardian.models.anomaly import BehavioralAnomalyDetector
from src.guardian.models.explain import ModelExplainer

def test_text_classifier_training_and_inference(tmp_path):
    train_df, test_df = generate_scam_corpus(n_samples=100, seed=42)
    clf = ScamTextClassifier()
    clf.fit(train_df["text"].tolist(), train_df["category"].tolist())
    
    res = clf.predict_risk("আপনার ওটিপি পিন কোড কাউকে দেবেন না")
    assert "scam_probability" in res
    assert 0.0 <= res["scam_probability"] <= 1.0
    
    # Save & reload verification
    model_path = os.path.join(tmp_path, "text_clf.joblib")
    clf.save(model_path)
    loaded = ScamTextClassifier.load(model_path)
    assert loaded.predict_risk("test")["scam_type"] in loaded.classes_

def test_lgb_transaction_model_and_shap(tmp_path):
    users = generate_users(n_users=50, seed=42)
    agents = generate_agents(n_agents=10, seed=42)
    texts_train, texts_test = generate_scam_corpus(n_samples=50, seed=42)
    txns = generate_transactions(users, agents, pd.concat([texts_train, texts_test]), n_txns=400, seed=42)
    
    G, risk_map = build_transaction_graph(txns, agents)
    txns = attach_graph_features(txns, risk_map)
    txns_feat = extract_behavioral_features(txns, users)
    
    split_idx = int(len(txns_feat) * 0.7)
    train_df = txns_feat.iloc[:split_idx]
    val_df = txns_feat.iloc[split_idx:]
    
    model = TransactionRiskModel()
    model.fit(train_df, train_df["label_scam"], val_df, val_df["label_scam"])
    
    preds = model.predict_risk(val_df)
    assert len(preds) == len(val_df)
    assert np.all((preds >= 0.0) & (preds <= 1.0))
    
    # SHAP Explainer verification
    explainer = ModelExplainer(model.model, model.feature_columns)
    sample_row = val_df.iloc[[0]]
    reasons = explainer.explain_instance(sample_row, top_k=2)
    assert isinstance(reasons, list)
    if len(reasons) > 0:
        assert "reason_code" in reasons[0]
        assert "bn" in reasons[0]

def test_anomaly_detector():
    df = pd.DataFrame({
        "amount_ratio_to_baseline": [1.0, 1.2, 0.9, 15.0],
        "velocity_count_1h": [0, 0, 1, 8],
        "is_odd_hour": [0, 0, 0, 1],
        "is_new_device": [0, 0, 0, 1]
    })
    anomaly = BehavioralAnomalyDetector()
    anomaly.fit(df.iloc[:3])
    scores = anomaly.score(df)
    assert len(scores) == 4
    # The 4th instance is heavily anomalous
    assert scores[3] > scores[0]