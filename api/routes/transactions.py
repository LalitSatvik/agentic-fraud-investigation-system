"""Transaction detail + on-demand scoring. The scorer is loaded once at
import time (module-level singleton) since loading the model artifacts per
request would be wasteful.

`fetch_and_score` is a plain function (no FastAPI `Depends`) so it can be
reused directly by api/routes/investigations.py, not just by the route below.
"""
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from api.db import get_db  # noqa: E402
from ml.scoring import FraudScorer  # noqa: E402

router = APIRouter(prefix="/internal/transactions", tags=["transactions"])

_scorer: Optional[FraudScorer] = None


def get_scorer() -> FraudScorer:
    global _scorer
    if _scorer is None:
        _scorer = FraudScorer()
    return _scorer


def fetch_and_score(transaction_id: str, db: Session) -> Optional[Dict[str, Any]]:
    row = db.execute(
        text("SELECT * FROM transactions WHERE transaction_id = :tid"), {"tid": transaction_id}
    ).mappings().first()
    if row is None:
        return None
    tx = dict(row)

    score = get_scorer().score_transaction(tx)

    return {
        "transaction_id": tx["transaction_id"],
        "step": tx["step"],
        "type": tx["type"],
        "amount": tx["amount"],
        "customer_id": tx["customer_id"],
        "counterparty_id": tx["counterparty_id"],
        "orig_balance_before": tx["orig_balance_before"],
        "orig_balance_after": tx["orig_balance_after"],
        "dest_balance_before": tx["dest_balance_before"],
        "dest_balance_after": tx["dest_balance_after"],
        "risk_score": score["risk_score"],
        "anomaly_score": score["anomaly_score"],
        "above_threshold": score["above_threshold"],
        "model_version": score["model_version"],
    }


@router.get("/{transaction_id}")
def get_transaction(transaction_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    result = fetch_and_score(transaction_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail=f"transaction {transaction_id} not found")
    return result
