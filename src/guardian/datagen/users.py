import numpy as np
import pandas as pd

def generate_users(n_users: int = 5000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    
    age_groups = ["18-25", "26-40", "41-60", "60+"]
    age_probs = [0.28, 0.42, 0.20, 0.10]
    regions = ["urban", "rural"]
    region_probs = [0.55, 0.45]
    
    user_ids = [f"U_{100000 + i}" for i in range(n_users)]
    user_ages = rng.choice(age_groups, size=n_users, p=age_probs)
    user_regions = rng.choice(regions, size=n_users, p=region_probs)
    tenure_days = rng.integers(10, 1200, size=n_users)
    has_trusted = rng.choice([True, False], size=n_users, p=[0.60, 0.40])
    
    # Calculate synthetic vulnerability score based on documented heuristics
    vulnerability_scores = []
    for age, reg, tenure in zip(user_ages, user_regions, tenure_days):
        score = 0.20
        if age == "60+":
            score += 0.40
        elif age == "41-60":
            score += 0.20
        elif age == "18-25":
            score += 0.10
            
        if reg == "rural":
            score += 0.20
        if tenure < 60:
            score += 0.20
        elif tenure < 180:
            score += 0.10
            
        # Add slight natural jitter
        score += rng.uniform(-0.05, 0.05)
        vulnerability_scores.append(float(np.clip(score, 0.05, 0.98)))
        
    typical_amounts = np.exp(rng.normal(6.5, 0.6, size=n_users)) # Median ~৳665, tail to ৳5000+
    device_ids = [f"DEV_{rng.integers(1000, 9999)}_{i}" for i in range(n_users)]
    
    return pd.DataFrame({
        "user_id": user_ids,
        "age_group": user_ages,
        "region": user_regions,
        "tenure_days": tenure_days,
        "vulnerability_score": np.round(vulnerability_scores, 3),
        "has_trusted_contact": has_trusted,
        "typical_amount": np.round(typical_amounts, 2),
        "primary_device_id": device_ids
    })

def generate_agents(n_agents: int = 300, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    agent_ids = [f"AG_{20000 + i}" for i in range(n_agents)]
    types = rng.choice(["agent_cashpoint", "merchant_retail", "super_agent"], size=n_agents, p=[0.70, 0.25, 0.05])
    regions = rng.choice(["urban", "rural"], size=n_agents, p=[0.60, 0.40])
    is_mule_cluster = rng.choice([True, False], size=n_agents, p=[0.05, 0.95])
    
    return pd.DataFrame({
        "entity_id": agent_ids,
        "entity_type": types,
        "region": regions,
        "is_flagged_mule_cluster": is_mule_cluster
    })