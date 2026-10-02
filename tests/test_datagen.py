import pytest
import pandas as pd
from src.guardian.datagen.users import generate_users, generate_agents
from src.guardian.datagen.scam_texts import generate_scam_corpus
from src.guardian.datagen.transactions import generate_transactions

def test_user_and_agent_generation():
    users = generate_users(n_users=100, seed=123)
    agents = generate_agents(n_agents=20, seed=123)
    
    assert len(users) == 100
    assert len(agents) == 20
    assert set(["user_id", "vulnerability_score", "typical_amount"]).issubset(users.columns)
    assert users["vulnerability_score"].between(0.0, 1.0).all()

def test_scam_corpus_zero_leakage_split():
    train_df, test_df = generate_scam_corpus(n_samples=120, seed=123)
    assert len(train_df) > 0
    assert len(test_df) > 0
    assert set(train_df["template_split"].unique()) == {"train_family"}
    assert set(test_df["template_split"].unique()) == {"unseen_test_family"}
    
    # Verify no raw sentence overlap across train and test template families
    train_texts = set(train_df["text"])
    test_texts = set(test_df["text"])
    assert len(train_texts.intersection(test_texts)) == 0

def test_transaction_generation_distributions():
    users = generate_users(n_users=50, seed=123)
    agents = generate_agents(n_agents=10, seed=123)
    train_texts, test_texts = generate_scam_corpus(n_samples=60, seed=123)
    texts = pd.concat([train_texts, test_texts])
    
    txns = generate_transactions(users, agents, texts, n_txns=500, seed=123)
    assert len(txns) == 500
    assert "label_scam" in txns.columns
    fraud_rate = txns["label_scam"].mean()
    assert 0.01 <= fraud_rate <= 0.05
    assert txns["timestamp"].is_monotonic_increasing