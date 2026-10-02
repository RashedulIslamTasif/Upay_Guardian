import numpy as np
import pandas as pd
from typing import Dict, Any

def extract_behavioral_features(
    txns_df: pd.DataFrame,
    users_df: pd.DataFrame
) -> pd.DataFrame:
    """Extract temporal, velocity, and deviation features strictly respecting time order."""
    df = txns_df.sort_values("timestamp").copy()
    
    # Merge user baseline demographics
    user_cols = ["user_id", "vulnerability_score", "tenure_days", "typical_amount", "primary_device_id", "has_trusted_contact"]
    df = df.merge(users_df[user_cols], on="user_id", how="left")
    
    # Deviation and mismatch indicators
    df["amount_ratio_to_baseline"] = np.round(df["amount"] / np.maximum(df["typical_amount"], 1.0), 3)
    df["is_new_device"] = (df["device_id"] != df["primary_device_id"]).astype(int)
    df["txn_hour"] = pd.to_datetime(df["timestamp"]).dt.hour
    df["is_odd_hour"] = df["txn_hour"].isin([23, 0, 1, 2, 3, 4, 5]).astype(int)
    
    # Track historical interaction state per user (preventing future data leakage)
    seen_recipients_by_user = {}
    is_new_recipient = []
    
    for _, row in df.iterrows():
        uid = row["user_id"]
        rec = row["recipient_id"]
        if uid not in seen_recipients_by_user:
            seen_recipients_by_user[uid] = set()
            is_new_recipient.append(1)
            seen_recipients_by_user[uid].add(rec)
        else:
            if rec in seen_recipients_by_user[uid]:
                is_new_recipient.append(0)
            else:
                is_new_recipient.append(1)
                seen_recipients_by_user[uid].add(rec)
                
    df["is_new_recipient"] = is_new_recipient
    
    # Velocity window features (1h and 24h rolling counts/sums per user)
    df["ts_dt"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("ts_dt")
    
    grouped = df.groupby("user_id")
    df["velocity_count_1h"] = grouped.rolling("1h")["txn_id"].count().values - 1
    df["velocity_count_24h"] = grouped.rolling("24h")["txn_id"].count().values - 1
    df["velocity_amount_24h"] = grouped.rolling("24h")["amount"].sum().values
    
    df = df.reset_index(drop=True)
    df["velocity_count_1h"] = df["velocity_count_1h"].clip(lower=0).fillna(0).astype(int)
    df["velocity_count_24h"] = df["velocity_count_24h"].clip(lower=0).fillna(0).astype(int)
    
    # Heuristic for "sent by mistake" refund pattern:
    # A send_money transaction to a new recipient with amount > 3000
    df["sent_by_mistake_risk_flag"] = (
        (df["type"] == "send_money") & 
        (df["is_new_recipient"] == 1) & 
        (df["amount"] >= 3000.0)
    ).astype(int)
    
    return df