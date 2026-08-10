"""
End-to-end demo runner: pulls a batch of "incoming" transactions, scores each
via the API (GET /internal/transactions/{id}, which runs the XGBoost model),
and for any that cross the risk threshold, triggers the Investigation Agent
(POST /investigations/{id}/run) — the same path a real streaming pipeline
would take on each new transaction, just batched here for a local demo
instead of event-driven.

Requires the API to already be running (api/main.py) with ANTHROPIC_API_KEY
set in its environment (the agent subprocess it spawns needs it).

Run:
    python pipeline/run_batch.py --num 20
"""
import argparse
import os
import sys
from pathlib import Path

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


def main(n: int, seed: int) -> None:
    tx = pd.read_parquet(ROOT / "data" / "processed" / "transactions.parquet")
    sample = tx.sample(n=n, random_state=seed)

    client = httpx.Client(base_url=API_BASE_URL, timeout=200.0)
    flagged = 0
    investigated = 0

    for _, row in sample.iterrows():
        txn_id = row["transaction_id"]
        detail = client.get(f"/internal/transactions/{txn_id}").json()
        marker = "FLAGGED" if detail["above_threshold"] else "clear  "
        print(f"[{marker}] {txn_id}  risk_score={detail['risk_score']:.4f}  amount=${detail['amount']:,.2f}  type={detail['type']}")

        if not detail["above_threshold"]:
            continue
        flagged += 1

        print("           -> above threshold, running Investigation Agent...")
        resp = client.post(f"/investigations/{txn_id}/run")
        if resp.status_code != 200:
            print(f"           -> investigation failed ({resp.status_code}): {resp.text[:300]}")
            continue

        inv = resp.json()
        report = inv.get("report") or {}
        investigated += 1
        print(
            f"           -> investigation #{inv['id']}: "
            f"recommended_action={report.get('recommended_action')!r} "
            f"confidence={report.get('confidence')!r} "
            f"cost=${inv.get('total_cost_usd') or 0:.4f}"
        )

    print(f"\n{flagged} of {n} transactions flagged, {investigated} investigations created.")
    print("Review queue: GET /investigations/flagged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--num", type=int, default=20, help="how many transactions to pull through the pipeline")
    parser.add_argument("--seed", type=int, default=123)
    args = parser.parse_args()
    main(args.num, args.seed)
