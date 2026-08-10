"""
Feature engineering for the base fraud classifier.

Deliberately transaction-level + causal customer-history aggregates only —
NOT the geo/IP/device/graph enrichment tables. Those are reserved for the
Investigation Agent's tools once a transaction is flagged; the base model
has to work with what's available at authorization time, same as a real
first-pass fraud model would.

Causal aggregates (prior_txn_count, prior_avg_amount, ...) are computed using
only transactions with a strictly earlier `step` for the same customer, so
there's no leakage from the future.

Run:
    python ml/features/build_features.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

TX_TYPES = ["CASH_OUT", "PAYMENT", "CASH_IN", "TRANSFER", "DEBIT"]


def build_features(tx: pd.DataFrame) -> pd.DataFrame:
    df = tx.copy()

    # --- balance-consistency features (classic PaySim signal: fraud txns often
    # don't conserve balance the way legitimate ones do) ---
    df["balance_delta_orig"] = df["orig_balance_before"] - df["orig_balance_after"]
    df["balance_delta_dest"] = df["dest_balance_after"] - df["dest_balance_before"]
    df["error_balance_orig"] = df["orig_balance_before"] - df["amount"] - df["orig_balance_after"]
    df["error_balance_dest"] = df["dest_balance_before"] + df["amount"] - df["dest_balance_after"]
    df["orig_balance_before_is_zero"] = (df["orig_balance_before"] == 0).astype(int)
    df["dest_balance_before_is_zero"] = (df["dest_balance_before"] == 0).astype(int)
    df["amount_to_orig_balance_ratio"] = df["amount"] / df["orig_balance_before"].replace(0, np.nan)
    df["amount_to_orig_balance_ratio"] = df["amount_to_orig_balance_ratio"].fillna(-1)

    # --- transaction-type one-hots ---
    for t in TX_TYPES:
        df[f"type_{t}"] = (df["type"] == t).astype(int)

    # --- time-of-day / counterparty shape ---
    df["hour_of_day"] = df["step"] % 24
    df["is_counterparty_merchant"] = df["counterparty_id"].str.startswith("M").astype(int)

    # --- causal customer-history aggregates (sorted by step, expanding window) ---
    df = df.sort_values(["customer_id", "step"]).reset_index(drop=True)
    grp = df.groupby("customer_id")["amount"]
    df["prior_txn_count"] = grp.cumcount()
    df["prior_avg_amount"] = grp.apply(lambda s: s.shift(1).expanding().mean()).reset_index(level=0, drop=True)
    df["prior_avg_amount"] = df["prior_avg_amount"].fillna(0)
    df["amount_vs_prior_avg_ratio"] = np.where(
        df["prior_avg_amount"] > 0, df["amount"] / df["prior_avg_amount"], -1
    )
    df["is_first_transaction"] = (df["prior_txn_count"] == 0).astype(int)

    return df


FEATURE_COLUMNS = [
    "amount",
    "orig_balance_before",
    "orig_balance_after",
    "dest_balance_before",
    "dest_balance_after",
    "balance_delta_orig",
    "balance_delta_dest",
    "error_balance_orig",
    "error_balance_dest",
    "orig_balance_before_is_zero",
    "dest_balance_before_is_zero",
    "amount_to_orig_balance_ratio",
    *[f"type_{t}" for t in TX_TYPES],
    "hour_of_day",
    "is_counterparty_merchant",
    "prior_txn_count",
    "prior_avg_amount",
    "amount_vs_prior_avg_ratio",
    "is_first_transaction",
]


def main() -> None:
    tx = pd.read_parquet(PROCESSED_DIR / "transactions.parquet")
    print(f"Loaded {len(tx):,} transactions")

    featured = build_features(tx)
    out_cols = ["transaction_id", "step", "customer_id", "is_fraud", *FEATURE_COLUMNS]
    featured = featured[out_cols]

    out_path = PROCESSED_DIR / "features.parquet"
    featured.to_parquet(out_path, index=False)
    print(f"Wrote {len(featured):,} rows x {len(FEATURE_COLUMNS)} features to {out_path}")


if __name__ == "__main__":
    main()
