"""
Curates the gold-standard evaluation set from our synthesized ground truth
(is_fraud, is_known_ring_member, and the injected device/geo/VPN signals) —
real transactions with known-correct outcomes, not hand-written fakes.

Five categories, ~4 cases each:
    clean_fraud_ring       confirmed fraud, ring-linked            -> must deny
    clean_fraud_takeover   confirmed fraud, new device + far geo   -> must deny
    clean_legit            legit, no red flags at all              -> must approve
    ambiguous_legit        legit BUT has a red flag (new device/   -> must NOT be a confident
                            geo mismatch/VPN) — a false-positive       "deny"; approve or escalate
                            trap for an over-eager agent               is acceptable
    ambiguous_fraud        confirmed fraud but device/geo/VPN      -> must NOT be a confident
                            look normal (relies on balance/history/    "approve"; deny or escalate
                            history signal) — a false-negative trap    is acceptable

Output: eval/gold_set/gold_set.json

Run:
    python eval/gold_set/build_gold_set.py
"""
import json
from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
OUT_PATH = Path(__file__).resolve().parent / "gold_set.json"

N_PER_CATEGORY = 4
SEED = 7


def load_joined() -> pd.DataFrame:
    tx = pd.read_parquet(PROCESSED_DIR / "transactions.parquet")
    ctx = pd.read_parquet(PROCESSED_DIR / "transaction_context.parquet")
    cust = pd.read_parquet(PROCESSED_DIR / "customers.parquet")[["customer_id", "is_known_ring_member"]]
    return tx.merge(ctx, on="transaction_id").merge(cust, on="customer_id")


def build_cases(df: pd.DataFrame) -> list:
    cases = []

    def sample(pool: pd.DataFrame, category: str, expected_action_set: list, keywords: list, notes: str, must_not: str = None):
        picked = pool.sample(n=min(N_PER_CATEGORY, len(pool)), random_state=SEED)
        for _, row in picked.iterrows():
            cases.append(
                {
                    "transaction_id": row["transaction_id"],
                    "category": category,
                    "ground_truth_is_fraud": bool(row["is_fraud"]),
                    "expected_action_set": expected_action_set,
                    "must_not_recommend": must_not,
                    "expected_evidence_keywords": keywords,
                    "notes": notes,
                }
            )

    sample(
        df[(df.is_fraud == 1) & df.is_known_ring_member],
        "clean_fraud_ring",
        ["deny"],
        ["ring", "link", "shared device", "network", "fraud rate"],
        "Confirmed fraud with a clear device-sharing ring signature — should be an unambiguous deny.",
        must_not="approve",
    )

    sample(
        df[(df.is_fraud == 1) & (~df.is_known_ring_member) & df.is_new_device_for_customer & (df.distance_from_home_km > 500)],
        "clean_fraud_takeover",
        ["deny"],
        ["new device", "distance", "mismatch", "home"],
        "Confirmed fraud, classic account-takeover signature (new device, far from home) — should be an unambiguous deny.",
        must_not="approve",
    )

    sample(
        df[(df.is_fraud == 0) & (~df.is_new_device_for_customer) & (~df.is_vpn_or_proxy) & (df.distance_from_home_km < 50)],
        "clean_legit",
        ["approve"],
        ["known device", "home", "match"],
        "Legitimate transaction with no red flags anywhere — should be an unambiguous approve.",
        must_not="deny",
    )

    sample(
        df[(df.is_fraud == 0) & (df.is_new_device_for_customer | df.is_vpn_or_proxy | (df.distance_from_home_km > 500))],
        "ambiguous_legit",
        ["approve", "escalate"],
        [],
        "Legitimate transaction but with a surface-level red flag (new device/VPN/distance) — a "
        "false-positive trap. A confident 'deny' here would be an over-eager agent.",
        must_not="deny",
    )

    sample(
        df[
            (df.is_fraud == 1)
            & (~df.is_known_ring_member)
            & (~df.is_new_device_for_customer)
            & (~df.is_vpn_or_proxy)
            & (df.distance_from_home_km < 50)
        ],
        "ambiguous_fraud",
        ["deny", "escalate"],
        ["prior", "history", "balance"],
        "Confirmed fraud with normal-looking device/geo/VPN signals — relies on balance/history "
        "evidence. A confident 'approve' here would be a false-negative trap.",
        must_not="approve",
    )

    return cases


def main() -> None:
    df = load_joined()
    cases = build_cases(df)
    OUT_PATH.write_text(json.dumps(cases, indent=2))
    print(f"Wrote {len(cases)} gold cases to {OUT_PATH}")
    for c in cases:
        print(f"  [{c['category']}] {c['transaction_id']}  expected={c['expected_action_set']}")


if __name__ == "__main__":
    main()
