import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

ANOMALY_FEATURES = [
    "amount_ratio_to_baseline",
    "velocity_count_1h",
    "is_odd_hour",
    "is_new_device"
]

class BehavioralAnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(
            n_estimators=150,
            contamination=0.03,
            max_samples="auto",
            random_state=42,
            n_jobs=-1
        )
        self.features = ANOMALY_FEATURES

    def fit(self, df: pd.DataFrame):
        X = df[self.features].fillna(0)
        self.model.fit(X)
        return self

    def score(self, df: pd.DataFrame) -> np.ndarray:
        """Outputs calibrated anomaly score in [0.0, 1.0], where 1.0 = highly abnormal."""
        X = df[self.features].fillna(0)
        # raw decision function is positive for inliers, negative for outliers
        raw_scores = self.model.decision_function(X)
        # Invert and normalize to 0.0 - 1.0 range
        norm_scores = 1.0 / (1.0 + np.exp(raw_scores * 8.0))
        return np.round(norm_scores, 4)

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({"model": self.model, "features": self.features}, path)

    @classmethod
    def load(cls, path: str):
        instance = cls()
        data = joblib.load(path)
        instance.model = data["model"]
        instance.features = data["features"]
        return instance