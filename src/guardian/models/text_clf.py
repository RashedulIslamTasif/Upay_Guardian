import os
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from typing import Dict, Any, List

class ScamTextClassifier:
    def __init__(self):
        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                min_df=2,
                max_features=15000,
                sublinear_tf=True
            )),
            ("clf", LogisticRegression(
                C=2.5,
                class_weight="balanced",
                max_iter=1000,
                random_state=42
            ))
        ])
        self.classes_ = []

    def fit(self, texts: List[str], labels: List[str]):
        self.pipeline.fit(texts, labels)
        self.classes_ = list(self.pipeline.named_steps["clf"].classes_)
        return self

    def predict_risk(self, text: str) -> Dict[str, Any]:
        """Offline inference with keyword and n-gram evidence attribution."""
        if not text or not text.strip():
            return {
                "scam_type": "benign",
                "scam_probability": 0.0,
                "evidence_phrases": [],
                "is_scam": False
            }

        probs = self.pipeline.predict_proba([text])[0]
        pred_idx = int(np.argmax(probs))
        pred_class = self.classes_[pred_idx]
        
        # Calculate scam probability as 1.0 - benign_prob
        benign_idx = self.classes_.index("benign") if "benign" in self.classes_ else -1
        scam_prob = float(1.0 - probs[benign_idx]) if benign_idx != -1 else float(probs[pred_idx])

        # Extract top salient features from the linear model for transparency
        tfidf = self.pipeline.named_steps["tfidf"]
        clf = self.pipeline.named_steps["clf"]
        feature_names = tfidf.get_feature_names_out()
        
        vec = tfidf.transform([text]).toarray()[0]
        nonzero_indices = np.where(vec > 0)[0]
        
        evidence = []
        if pred_class != "benign" and len(nonzero_indices) > 0:
            coefs = clf.coef_[pred_idx]
            salient = [(feature_names[i], vec[i] * coefs[i]) for i in nonzero_indices]
            salient = sorted(salient, key=lambda x: x[1], reverse=True)
            evidence = [term.strip() for term, score in salient[:4] if score > 0 and len(term.strip()) > 1]

        return {
            "scam_type": pred_class,
            "scam_probability": round(scam_prob, 4),
            "evidence_phrases": evidence,
            "is_scam": scam_prob >= 0.50
        }

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({"pipeline": self.pipeline, "classes": self.classes_}, path)

    @classmethod
    def load(cls, path: str):
        instance = cls()
        data = joblib.load(path)
        instance.pipeline = data["pipeline"]
        instance.classes_ = data["classes"]
        return instance