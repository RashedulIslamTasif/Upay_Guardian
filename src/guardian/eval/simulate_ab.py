import numpy as np
import pandas as pd
from typing import Dict, Any, List

# Documented empirical assumptions for intervention efficacy
DEFAULT_EFFICACY = {
    "L0": {"scam_stop_rate": 0.00, "legit_abandon_rate": 0.000},
    "L1": {"scam_stop_rate": 0.35, "legit_abandon_rate": 0.002},
    "L2": {"scam_stop_rate": 0.70, "legit_abandon_rate": 0.008},
    "L3": {"scam_stop_rate": 0.88, "legit_abandon_rate": 0.015},
    "L4": {"scam_stop_rate": 0.96, "legit_abandon_rate": 0.020},
}

def simulate_business_outcomes(
    test_df: pd.DataFrame,
    assigned_levels: List[str],
    efficacy: Dict[str, Dict[str, float]] = DEFAULT_EFFICACY,
    analyst_minutes_saved_per_case: float = 6.0
) -> Dict[str, Any]:
    """Simulates A/B counterfactual impact: Control (No Guardian) vs Treatment (Guardian)."""
    df = test_df.copy()
    df["assigned_level"] = assigned_levels

    # Financial loss baseline in control group
    total_scam_txns = int((df["label_scam"] == 1).sum())
    total_scam_bdt = float(df[df["label_scam"] == 1]["amount"].sum())
    total_legit_txns = int((df["label_scam"] == 0).sum())
    total_legit_bdt = float(df[df["label_scam"] == 0]["amount"].sum())

    # Calculate treatment outcomes
    prevented_loss_bdt = 0.0
    prevented_scam_count = 0
    delayed_legit_count = 0
    delayed_legit_bdt = 0.0
    analyst_cases = 0

    for _, row in df.iterrows():
        lvl = row["assigned_level"]
        is_scam = (row["label_scam"] == 1)
        amt = row["amount"]
        eff = efficacy.get(lvl, {"scam_stop_rate": 0.0, "legit_abandon_rate": 0.0})

        if is_scam:
            prevented_loss_bdt += amt * eff["scam_stop_rate"]
            if eff["scam_stop_rate"] >= 0.50:
                prevented_scam_count += 1
        else:
            # Friction imposed on legitimate customer
            if lvl in ["L2", "L3", "L4"]:
                delayed_legit_count += 1
                delayed_legit_bdt += amt

        if lvl == "L4":
            analyst_cases += 1

    loss_reduction_pct = (prevented_loss_bdt / max(total_scam_bdt, 1.0)) * 100.0
    legit_friction_rate = (delayed_legit_count / max(total_legit_txns, 1.0)) * 100.0
    analyst_hours_saved = (analyst_cases * analyst_minutes_saved_per_case) / 60.0

    return {
        "baseline_scam_loss_bdt": round(total_scam_bdt, 2),
        "prevented_loss_bdt": round(prevented_loss_bdt, 2),
        "loss_reduction_pct": round(loss_reduction_pct, 2),
        "scams_intervened_count": prevented_scam_count,
        "total_scam_count": total_scam_txns,
        "legit_friction_rate_pct": round(legit_friction_rate, 2),
        "delayed_legit_txns_count": delayed_legit_count,
        "delayed_legit_bdt": round(delayed_legit_bdt, 2),
        "analyst_queue_cases": analyst_cases,
        "analyst_hours_saved": round(analyst_hours_saved, 1)
    }

def generate_tradeoff_curve(
    test_df: pd.DataFrame,
    y_probs: np.ndarray,
    efficacy: Dict[str, Dict[str, float]] = DEFAULT_EFFICACY
) -> List[Dict[str, Any]]:
    """Generates Loss Prevented vs Legit Friction curve across threshold settings."""
    thresholds = [0.20, 0.35, 0.50, 0.65, 0.75, 0.85]
    curve = []

    for t in thresholds:
        simulated_levels = []
        for p in y_probs:
            if p >= t + 0.25:
                simulated_levels.append("L4")
            elif p >= t + 0.15:
                simulated_levels.append("L3")
            elif p >= t:
                simulated_levels.append("L2")
            elif p >= (t - 0.15):
                simulated_levels.append("L1")
            else:
                simulated_levels.append("L0")

        res = simulate_business_outcomes(test_df, simulated_levels, efficacy)
        curve.append({
            "threshold": t,
            "loss_reduction_pct": res["loss_reduction_pct"],
            "legit_friction_rate_pct": res["legit_friction_rate_pct"],
            "prevented_loss_bdt": res["prevented_loss_bdt"],
            "analyst_cases": res["analyst_queue_cases"]
        })
    return curve