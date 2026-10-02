import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve, auc, roc_auc_score, f1_score, confusion_matrix
from typing import Dict, Any

def evaluate_model_performance(y_true: np.ndarray, y_probs: np.ndarray) -> Dict[str, Any]:
    """Calculates PR-AUC, ROC-AUC, and fixed-capacity review metrics."""
    precision, recall, _ = precision_recall_curve(y_true, y_probs)
    pr_auc = auc(recall, precision)
    roc_auc = roc_auc_score(y_true, y_probs)

    # Fixed capacity evaluation: Top 1% and 2% highest-risk transactions flagged
    n = len(y_probs)
    top_1_cutoff = np.percentile(y_probs, 99)
    top_2_cutoff = np.percentile(y_probs, 98)

    pred_top_1 = (y_probs >= top_1_cutoff).astype(int)
    pred_top_2 = (y_probs >= top_2_cutoff).astype(int)

    recall_at_1 = float(np.sum((pred_top_1 == 1) & (y_true == 1)) / max(np.sum(y_true == 1), 1))
    recall_at_2 = float(np.sum((pred_top_2 == 1) & (y_true == 1)) / max(np.sum(y_true == 1), 1))

    return {
        "pr_auc": round(float(pr_auc), 4),
        "roc_auc": round(float(roc_auc), 4),
        "recall_at_1_percent_capacity": round(recall_at_1, 4),
        "recall_at_2_percent_capacity": round(recall_at_2, 4)
    }

def evaluate_text_unseen_split(test_df: pd.DataFrame, text_clf) -> Dict[str, Any]:
    """Evaluates scam text classifier strictly on unseen template families."""
    preds = []
    for txt in test_df["text"]:
        res = text_clf.predict_risk(txt)
        preds.append(res["scam_type"])

    y_true = test_df["category"].tolist()
    macro_f1 = f1_score(y_true, preds, average="macro", zero_division=0)
    cm = confusion_matrix(y_true, preds, labels=text_clf.classes_)

    return {
        "unseen_template_macro_f1": round(float(macro_f1), 4),
        "classes": text_clf.classes_,
        "confusion_matrix": cm.tolist()
    }