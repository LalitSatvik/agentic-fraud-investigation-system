"""
Downsample the raw PaySim log (6.36M rows) into a tractable base transaction set
for this project: keep every fraudulent transaction, plus a random sample of
legitimate ones, so the resulting dataset is still heavily imbalanced (realistic)
but small enough to train/serve/demo comfortably.

Input:  data/raw/paysim/PS_20174392719_1491204439457_log.csv
Output: data/processed/transactions_base.parquet

Run:
    python data/generators/sample_paysim.py
"""
import argparse
from pathlib import Path

import pandas as pd

RAW_PATH = Path(__file__).resolve().parents[1] / "raw" / "paysim" / "PS_20174392719_1491204439457_log.csv"
OUT_PATH = Path(__file__).resolve().parents[1] / "processed" / "transactions_base.parquet"


def main(non_fraud_sample: int, seed: int) -> None:
    print(f"Reading {RAW_PATH} ...")
    df = pd.read_csv(RAW_PATH)
    print(f"Loaded {len(df):,} rows, {df['isFraud'].sum():,} fraudulent ({df['isFraud'].mean():.4%})")

    fraud = df[df["isFraud"] == 1]
    non_fraud = df[df["isFraud"] == 0].sample(n=non_fraud_sample, random_state=seed)

    sampled = pd.concat([fraud, non_fraud], ignore_index=True)
    sampled = sampled.sample(frac=1, random_state=seed).reset_index(drop=True)  # shuffle

    # Stable, human-legible transaction id
    sampled.insert(0, "transaction_id", [f"TXN{100000 + i}" for i in range(len(sampled))])
    sampled = sampled.rename(
        columns={
            # PaySim's nameOrig is ~unique per row (no repeat customers), so it can't carry
            # "customer history" signal on its own — kept as a raw reference; the enrichment
            # step assigns a persistent synthetic customer_id with realistic repeat behavior.
            "nameOrig": "paysim_account_ref",
            "nameDest": "counterparty_id",
            "oldbalanceOrg": "orig_balance_before",
            "newbalanceOrig": "orig_balance_after",
            "oldbalanceDest": "dest_balance_before",
            "newbalanceDest": "dest_balance_after",
            "isFraud": "is_fraud",
            "isFlaggedFraud": "is_flagged_rule_based",
        }
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    sampled.to_parquet(OUT_PATH, index=False)
    print(f"Wrote {len(sampled):,} rows ({sampled['is_fraud'].sum():,} fraud, "
          f"{sampled['is_fraud'].mean():.3%}) to {OUT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--non-fraud-sample", type=int, default=150_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    main(args.non_fraud_sample, args.seed)
