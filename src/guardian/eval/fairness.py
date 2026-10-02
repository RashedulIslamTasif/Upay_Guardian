import pandas as pd
import numpy as np
from typing import Dict, Any, List

def evaluate_demographic_fairness(
    test_df: pd.DataFrame,
    assigned_levels: List[str]
) -> Dict[str, Any]:
    """Audits False Positive Rate and Friction Disparity across age, region, and tenure."""
    df = test_df.copy()
    df["assigned_level"] = assigned_levels
    df["has_friction"] = df["assigned_level"].isin(["L2", "L3", "L4"]).astype(int)
    df["is_false_positive"] = ((df["label_scam"] == 0) & (df["has_friction"] == 1)).astype(int)

    def _summarize_slice(col_name: str) -> List[Dict[str, Any]]:
        if col_name not in df.columns:
            return []
        slice_stats = []
        for val, grp in df.groupby(col_name, observed=False):
            n_legit = max(int((grp["label_scam"] == 0).sum()), 1)
            n_scam = max(int((grp["label_scam"] == 1).sum()), 1)

            fpr = (grp["is_false_positive"].sum() / n_legit) * 100.0
            recall = (grp[(grp["label_scam"] == 1) & (grp["has_friction"] == 1)].shape[0] / n_scam) * 100.0
            friction_rate = (grp["has_friction"].mean()) * 100.0

            slice_stats.append({
                "segment": str(val),
                "sample_size": len(grp),
                "false_positive_rate_pct": round(float(fpr), 2),
                "detection_recall_pct": round(float(recall), 2),
                "overall_friction_pct": round(float(friction_rate), 2)
            })
        return slice_stats

    # Tenure cohorts
    if "tenure_days" in df.columns:
        df["tenure_cohort"] = pd.cut(
            df["tenure_days"],
            bins=[-1, 90, 365, 5000],
            labels=["New (<90d)", "Mid (90-365d)", "Established (>365d)"]
        )

    return {
        "by_age_group": _summarize_slice("age_group"),
        "by_region": _summarize_slice("region"),
        "by_tenure": _summarize_slice("tenure_cohort")
    }