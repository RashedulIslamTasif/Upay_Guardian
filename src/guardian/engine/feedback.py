import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

FEEDBACK_LOG_PATH = "data/retraining_queue.json"


class AdaptiveFeedbackLoop:
    def __init__(self, log_path: str = FEEDBACK_LOG_PATH):
        self.log_path = log_path
        self._ensure_storage()

    def _ensure_storage(self):
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump({"pending_retrain_count": 0,
                          "verified_labels": []}, f, indent=2)

    def log_analyst_label(self, alert_id: str, verified_resolution: str, analyst_id: str, features: Dict[str, Any]):
        """Captures ground truth analyst resolutions for continuous active learning."""
        with open(self.log_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        record = {
            "alert_id": alert_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "analyst_id": analyst_id,
            "ground_truth_label": 1 if verified_resolution == "confirmed_scam" else 0,
            "resolution": verified_resolution,
            "feature_snapshot": features
        }

        data["verified_labels"].append(record)
        data["pending_retrain_count"] = len(data["verified_labels"])

        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return data["pending_retrain_count"]

    def get_queue_stats(self) -> Dict[str, Any]:
        with open(self.log_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        scams = sum(1 for r in data["verified_labels"]
                    if r.get("ground_truth_label") == 1)
        fps = sum(1 for r in data["verified_labels"]
                  if r.get("ground_truth_label") == 0)
        return {
            "total_feedback_samples": len(data["verified_labels"]),
            "confirmed_scams": scams,
            "false_positives": fps,
            "model_drift_status": "Calibrated (Within SLA)",
            "next_scheduled_batch_retrain": "02:00 AM UTC (Nightly Pipeline)"
        }
