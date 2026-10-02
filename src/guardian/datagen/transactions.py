import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_transactions(
    users_df: pd.DataFrame,
    agents_df: pd.DataFrame,
    scam_texts_df: pd.DataFrame,
    n_txns: int = 150000,
    seed: int = 42
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    start_date = datetime(2026, 7, 5, 0, 0, 0)
    end_date = datetime(2026, 10, 3, 23, 59, 59)
    total_seconds = int((end_date - start_date).total_seconds())
    
    user_lookup = users_df.set_index("user_id").to_dict("index")
    user_ids = users_df["user_id"].values
    agent_ids = agents_df["entity_id"].values
    mule_agents = agents_df[agents_df["is_flagged_mule_cluster"]]["entity_id"].values
    
    # 98% Normal, 2% Target Fraud Topology
    n_fraud = int(n_txns * 0.02)
    n_normal = n_txns - n_fraud
    
    records = []
    
    # Generate Normal Transactions
    normal_senders = rng.choice(user_ids, size=n_normal)
    random_offsets = rng.integers(0, total_seconds, size=n_normal)
    
    for uid, offset in zip(normal_senders, random_offsets):
        meta = user_lookup[uid]
        ts = start_date + timedelta(seconds=int(offset))
        
        # Diurnal distribution preference (normal active hours 08:00 - 22:00)
        hour = ts.hour
        hour_prob = 0.95 if (8 <= hour <= 22) else 0.40
        if rng.random() > hour_prob:
            ts = ts.replace(hour=int(rng.integers(8, 22)))
            
        base_amt = meta["typical_amount"]
        amt = float(np.clip(rng.normal(base_amt, base_amt * 0.3), 50.0, 25000.0))
        
        txn_type = rng.choice(["send_money", "cash_out", "mobile_recharge", "payment"], p=[0.45, 0.25, 0.20, 0.10])
        recipient = str(rng.choice(agent_ids)) if txn_type in ["cash_out", "payment"] else str(rng.choice(user_ids))
        
        records.append({
            "txn_id": "",
            "timestamp": ts,
            "user_id": uid,
            "type": txn_type,
            "amount": round(amt, 2),
            "recipient_id": recipient,
            "device_id": meta["primary_device_id"],
            "channel": "app",
            "region": meta["region"],
            "label_scam": 0,
            "scam_type": "none",
            "is_victim_initiated": True,
            "msg_context_id": None
        })
        
    # Generate Injected Scam Scenarios
    scam_types = ["otp_pin_theft", "fake_agent_support", "sent_by_mistake_refund", "fake_prize_fee", "mule_network"]
    scam_msgs = scam_texts_df[scam_texts_df["label"] == 1].to_dict("records")
    
    for i in range(n_fraud):
        stype = scam_types[i % len(scam_types)]
        # Bias fraud toward vulnerable users
        vulnerable_candidates = users_df[users_df["vulnerability_score"] >= 0.50]["user_id"].values
        uid = str(rng.choice(vulnerable_candidates if len(vulnerable_candidates) > 0 else user_ids))
        meta = user_lookup[uid]
        
        ts = start_date + timedelta(seconds=int(rng.integers(0, total_seconds)))
        msg = scam_msgs[rng.integers(0, len(scam_msgs))] if scam_msgs else None
        msg_id = msg["msg_id"] if msg else None
        
        if stype == "otp_pin_theft":
            amt = float(round(meta["typical_amount"] * rng.uniform(4.0, 9.0), 2))
            records.append({
                "txn_id": "",
                "timestamp": ts,
                "user_id": uid,
                "type": "send_money",
                "amount": amt,
                "recipient_id": f"MULE_{rng.integers(9000, 9999)}",
                "device_id": f"UNSEEN_DEV_{rng.integers(100, 999)}",
                "channel": "app",
                "region": meta["region"],
                "label_scam": 1,
                "scam_type": stype,
                "is_victim_initiated": False,
                "msg_context_id": msg_id
            })
        elif stype == "fake_agent_support":
            ts = ts.replace(hour=int(rng.choice([1, 2, 3, 4, 23]))) # Odd night hours
            amt = float(round(meta["typical_amount"] * rng.uniform(3.5, 6.0), 2))
            records.append({
                "txn_id": "",
                "timestamp": ts,
                "user_id": uid,
                "type": "send_money",
                "amount": amt,
                "recipient_id": f"FAKE_AGENT_{rng.integers(500, 999)}",
                "device_id": meta["primary_device_id"],
                "channel": "app",
                "region": meta["region"],
                "label_scam": 1,
                "scam_type": stype,
                "is_victim_initiated": True,
                "msg_context_id": msg_id
            })
        elif stype == "sent_by_mistake_refund":
            amt = float(round(rng.uniform(3500.0, 12000.0), 2))
            records.append({
                "txn_id": "",
                "timestamp": ts,
                "user_id": uid,
                "type": "send_money",
                "amount": amt,
                "recipient_id": f"REFUND_TARGET_{rng.integers(100, 500)}",
                "device_id": meta["primary_device_id"],
                "channel": "app",
                "region": meta["region"],
                "label_scam": 1,
                "scam_type": stype,
                "is_victim_initiated": True,
                "msg_context_id": msg_id
            })
        elif stype == "fake_prize_fee":
            amt = float(round(rng.uniform(400.0, 1800.0), 2))
            records.append({
                "txn_id": "",
                "timestamp": ts,
                "user_id": uid,
                "type": "payment",
                "amount": amt,
                "recipient_id": f"PRIZE_SYNDICATE_{rng.integers(10, 99)}",
                "device_id": meta["primary_device_id"],
                "channel": "app",
                "region": meta["region"],
                "label_scam": 1,
                "scam_type": stype,
                "is_victim_initiated": True,
                "msg_context_id": msg_id
            })
        elif stype == "mule_network":
            dest = str(rng.choice(mule_agents)) if len(mule_agents) > 0 else f"MULE_NODE_{rng.integers(10, 50)}"
            amt = float(round(meta["typical_amount"] * rng.uniform(2.5, 5.0), 2))
            records.append({
                "txn_id": "",
                "timestamp": ts,
                "user_id": uid,
                "type": "cash_out",
                "amount": amt,
                "recipient_id": dest,
                "device_id": meta["primary_device_id"],
                "channel": "ussd" if rng.random() > 0.5 else "app",
                "region": meta["region"],
                "label_scam": 1,
                "scam_type": stype,
                "is_victim_initiated": True,
                "msg_context_id": None
            })
            
    df = pd.DataFrame(records).sort_values("timestamp").reset_index(drop=True)
    df["txn_id"] = [f"TXN_{2026000000 + i}" for i in range(len(df))]
    return df