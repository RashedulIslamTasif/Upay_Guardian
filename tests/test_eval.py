import pytest
import numpy as np
import pandas as pd
from src.guardian.eval.metrics import evaluate_model_performance
from src.guardian.eval.simulate_ab import simulate_business_outcomes, generate_tradeoff_curve
from src.guardian.eval.fairness import evaluate_demographic_fairness

def test_model_performance_metrics():
    y_true = np.array([0, 0, 0, 1, 0, 1, 0, 0, 1, 0] * 10)
    y_probs = np.array([0.1, 0.2, 0.05, 0.9, 0.3, 0.85, 0.15, 0.02, 0.95, 0.4] * 10)
    res = evaluate_model_performance(y_true, y_probs)
    assert 0.0 <= res["pr_auc"] <= 1.0
    assert 0.0 <= res["recall_at_1_percent_capacity"] <= 1.0

def test_business_simulation_and_tradeoff():
    df = pd.DataFrame({
        "amount": [1000.0, 5000.0, 8000.0, 200.0],
        "label_scam": [0, 1, 1, 0]
    })
    assigned = ["L0", "L2", "L3", "L0"]
    outcomes = simulate_business_outcomes(df, assigned)
    assert outcomes["prevented_loss_bdt"] > 0
    assert outcomes["loss_reduction_pct"] > 0
    assert 0.0 <= outcomes["legit_friction_rate_pct"] <= 100.0

    curve = generate_tradeoff_curve(df, np.array([0.1, 0.65, 0.85, 0.05]))
    assert len(curve) > 0

def test_demographic_fairness_parity():
    df = pd.DataFrame({
        "label_scam": [0, 0, 1, 0],
        "age_group": ["18-25", "60+", "60+", "26-40"],
        "region": ["urban", "rural", "rural", "urban"],
        "tenure_days": [20, 45, 500, 100]
    })
    fairness = evaluate_demographic_fairness(df, ["L0", "L1", "L3", "L0"])
    assert "by_age_group" in fairness
    assert "by_region" in fairness
    assert "by_tenure" in fairness