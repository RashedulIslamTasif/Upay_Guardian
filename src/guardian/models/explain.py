import os
import joblib
import numpy as np
import pandas as pd
import shap
from typing import List, Dict, Any

REASON_MAPPINGS = {
    "amount_ratio_to_baseline": {
        "code": "AMOUNT_SPIKE",
        "bn": "লেনদেনের পরিমাণ আপনার স্বাভাবিক সীমার চেয়ে বহু গুণ বেশি।",
        "en": "Transaction amount is significantly higher than your typical baseline."
    },
    "is_new_device": {
        "code": "NEW_DEVICE",
        "bn": "লেনদেনটি একটি অপরিচিত বা নতুন ডিভাইস থেকে সম্পাদন করা হচ্ছে।",
        "en": "Transaction is initiated from an unrecognized device."
    },
    "is_new_recipient": {
        "code": "NEW_RECIPIENT",
        "bn": "প্রাপকের নম্বরটি আপনার জন্য একদম নতুন।",
        "en": "Recipient wallet has no prior history with your account."
    },
    "recipient_graph_risk": {
        "code": "MULE_CLUSTER_LINK",
        "bn": "প্রাপকের অ্যাকাউন্টটি সম্ভাব্য প্রতারক বা মানি-মিউল নেটওয়ার্কের সাথে যুক্ত।",
        "en": "Recipient is linked to suspicious aggregator or mule networks."
    },
    "sent_by_mistake_risk_flag": {
        "code": "REFUND_SCAM_PATTERN",
        "bn": "ভুল করে টাকা পাঠানোর দাবি ও দ্রুত বড় অঙ্কের ট্রানজেকশনের ধরন মিলে যাচ্ছে।",
        "en": "Pattern matches high-risk 'sent-by-mistake' refund manipulation."
    },
    "is_odd_hour": {
        "code": "ODD_HOURS_ACTIVITY",
        "bn": "গভীর রাতে বা অস্বাভাবিক সময়ে উচ্চ ঝুঁকিপূর্ণ লেনদেনের চেষ্টা।",
        "en": "Transaction occurred during unusual late-night hours."
    },
    "velocity_count_1h": {
        "code": "RAPID_VELOCITY",
        "bn": "স্বল্প সময়ের মধ্যে অস্বাভাবিক ঘন ঘন লেনদেন হচ্ছে।",
        "en": "Unusual high frequency of transactions within a short window."
    }
}

class ModelExplainer:
    def __init__(self, lgb_model, feature_names: List[str]):
        self.explainer = shap.TreeExplainer(lgb_model)
        self.feature_names = feature_names

    def explain_instance(self, single_row_df: pd.DataFrame, top_k: int = 3) -> List[Dict[str, Any]]:
        X = single_row_df[self.feature_names].copy()
        shap_values = self.explainer.shap_values(X)
        
        # Binary LightGBM SHAP handling
        sv = shap_values[1][0] if isinstance(shap_values, list) else shap_values[0]
        
        ranked_idx = np.argsort(sv)[::-1]
        reasons = []
        for idx in ranked_idx:
            feat = self.feature_names[idx]
            val = float(X.iloc[0][feat])
            impact = float(sv[idx])
            
            # Attribute only features driving risk upward
            if impact > 0.05 and feat in REASON_MAPPINGS:
                meta = REASON_MAPPINGS[feat]
                reasons.append({
                    "reason_code": meta["code"],
                    "feature": feat,
                    "value": val,
                    "shap_impact": round(impact, 3),
                    "bn": meta["bn"],
                    "en": meta["en"]
                })
            if len(reasons) >= top_k:
                break
                
        return reasons

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({"explainer": self.explainer, "features": self.feature_names}, path)

    @classmethod
    def load(cls, path: str):
        data = joblib.load(path)
        instance = cls.__new__(cls)
        instance.explainer = data["explainer"]
        instance.feature_names = data["features"]
        return instance