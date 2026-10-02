import argparse
import os
import pandas as pd
from src.guardian.datagen.users import generate_users, generate_agents
from src.guardian.datagen.scam_texts import generate_scam_corpus
from src.guardian.datagen.transactions import generate_transactions

def run_generation(n_users: int = 5000, n_agents: int = 300, n_txns: int = 150000, n_texts: int = 6000, seed: int = 42, output_dir: str = "data"):
    print(f"[*] Initializing Guardian Synthetic Generator (Seed={seed})...")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "sample"), exist_ok=True)
    
    print(f"[-] Synthesizing {n_users} users and {n_agents} agents...")
    users_df = generate_users(n_users=n_users, seed=seed)
    agents_df = generate_agents(n_agents=n_agents, seed=seed)
    
    print(f"[-] Generating {n_texts} slot-varied multilingual text messages with template splits...")
    train_texts, test_texts = generate_scam_corpus(n_samples=n_texts, seed=seed)
    all_texts = pd.concat([train_texts, test_texts]).reset_index(drop=True)
    
    print(f"[-] Simulating {n_txns} transactions across 90-day horizon with 5 fraud topologies...")
    txns_df = generate_transactions(users_df, agents_df, all_texts, n_txns=n_txns, seed=seed)
    
    # Save datasets
    print("[-] Persisting full datasets to disk...")
    users_df.to_parquet(os.path.join(output_dir, "users.parquet"), index=False)
    agents_df.to_parquet(os.path.join(output_dir, "agents.parquet"), index=False)
    all_texts.to_parquet(os.path.join(output_dir, "scam_texts.parquet"), index=False)
    txns_df.to_parquet(os.path.join(output_dir, "transactions.parquet"), index=False)
    
    train_texts.to_parquet(os.path.join(output_dir, "scam_texts_train.parquet"), index=False)
    test_texts.to_parquet(os.path.join(output_dir, "scam_texts_test.parquet"), index=False)
    
    # Save git-committable sample files (200 rows each)
    print("[-] Exporting 200-row samples to data/sample/...")
    users_df.head(200).to_csv(os.path.join(output_dir, "sample", "users_sample.csv"), index=False)
    agents_df.head(200).to_csv(os.path.join(output_dir, "sample", "agents_sample.csv"), index=False)
    all_texts.head(200).to_csv(os.path.join(output_dir, "sample", "scam_texts_sample.csv"), index=False)
    txns_df.head(200).to_csv(os.path.join(output_dir, "sample", "transactions_sample.csv"), index=False)
    
    fraud_rate = txns_df['label_scam'].mean() * 100
    print(f"[✓] Generation Complete! Total Txns: {len(txns_df):,} | Fraud Rate: {fraud_rate:.2f}% | Output: {output_dir}/")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Guardian Synthetic Data Generator")
    parser.add_argument("--users", type=int, default=5000)
    parser.add_argument("--agents", type=int, default=300)
    parser.add_argument("--txns", type=int, default=150000)
    parser.add_argument("--texts", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output_dir", type=str, default="data")
    args = parser.parse_args()
    
    run_generation(
        n_users=args.users,
        n_agents=args.agents,
        n_txns=args.txns,
        n_texts=args.texts,
        seed=args.seed,
        output_dir=args.output_dir
    )