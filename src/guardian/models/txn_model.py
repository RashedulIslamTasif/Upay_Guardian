import os
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.calibration import CalibratedClassifierCV
from typing import Dict, Any, List, Tuple

FEATURE_COLUMNS = [
    "amount_ratio_to_baseline",
    "is_new_device",
    "is_new_recipient",
    "is_odd_hour",
    "velocity_count_1h",
    "velocity_count_24h",
    "velocity_amount_24h",
    "recipient_graph_risk",
    "vulnerability_score",
    "tenure_days",
    "sent_by_mistake_risk_flag"
]

class TransactionRiskModel:
    def __init__(self):
        self.model = None
        self.calibrated_model = None
        self.feature_columns = FEATURE_COLUMNS

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame, y_val: pd.Series):
        X_tr = X_train[self.feature_columns].copy()
        X_v = X_val[self.feature_columns].copy()

        base_lgb = lgb.LGBMClassifier(
            n_estimators=300,
            learning_rate=0.03,
            max_depth=5,
            num_leaves=31,
            scale_pos_weight=15.0, # Counteract synthetic class imbalance
            random_state=42,
            verbosity=-1
        )
        base_lgb.fit(
            X_tr, y_train,
            eval_set=[(X_v, y_val)],
            callbacks=[lgb.early_stopping(stopping_rounds=25, verbose=False)]
        )
        self.model = base_lgb

        # Calibrate probabilities across all scikit-learn versions
        try:
            # scikit-learn >= 1.4 / 1.6+ using FrozenEstimator
            from sklearn.frozen import FrozenEstimator
            self.calibrated_model = CalibratedClassifierCV(estimator=FrozenEstimator(self.model), method="sigmoid")
            self.calibrated_model.fit(X_v, y_val)
        except (ImportError, Exception):
            try:
                # Legacy scikit-learn
                self.calibrated_model = CalibratedClassifierCV(estimator=self.model, method="sigmoid", cv="prefit")
                self.calibrated_model.fit(X_v, y_val)
            except Exception:
                # Robust fallback directly to the uncalibrated tree probabilities
                self.calibrated_model = self.model

        return self

    def predict_risk(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.feature_columns].copy()
        if self.calibrated_model is not None:
            probs = self.calibrated_model.predict_proba(X)[:, 1]
        else:
            probs = self.model.predict_proba(X)[:, 1]
        return np.round(probs, 4)

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({
            "model": self.model,
            "calibrated_model": self.calibrated_model,
            "features": self.feature_columns
        }, path)

    @classmethod
    def load(cls, path: str):
        instance = cls()
        data = joblib.load(path)
        instance.model = data["model"]
        instance.calibrated_model = data.get("calibrated_model", data["model"])
        instance.feature_columns = data["features"]
        return instance