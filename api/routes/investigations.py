"""
The review-queue + human-in-the-loop endpoints.

POST /investigations/{transaction_id}/run   — score + (if above threshold) run the
                                               Investigation Agent, persist as pending_review
GET  /investigations/flagged                — the review queue
GET  /investigations/stats                  — aggregate counts for the dashboard
GET  /investigations/{id}                   — full report + evidence trace
POST /investigations/{id}/decision          — human approve / reject / request more investigation

The agent runs in a separate Python environment (3.10+, required by its SDK) from the
API, so it's invoked as a subprocess rather than imported directly — set AGENT_PYTHON_BIN
to that environment's interpreter. Its CLI entrypoint (agent/investigate.py) prints one
JSON blob to stdout.
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from api.db import engine  # noqa: E402
from api.models.investigation import (  # noqa: E402
    STATUS_APPROVED,
    STATUS_MORE_INVESTIGATION_REQUESTED,
    STATUS_PENDING_REVIEW,
    STATUS_REJECTED,
    AuditLogEntry,
    Investigation,
)
from api.routes.transactions import fetch_and_score  # noqa: E402
from api.db import get_db as get_core_db  # noqa: E402

router = APIRouter(prefix="/investigations", tags=["investigations"])

AGENT_PYTHON_BIN = os.environ.get("AGENT_PYTHON_BIN", "python")
AGENT_TIMEOUT_SECONDS = int(os.environ.get("AGENT_TIMEOUT_SECONDS", "180"))

VALID_DECISIONS = {STATUS_APPROVED, STATUS_REJECTED, STATUS_MORE_INVESTIGATION_REQUESTED}


def get_session():
    # expire_on_commit=False: this handler commits more than once per request (the
    # investigation row, then each audit-log entry) — without this, SQLAlchemy expires
    # `inv`'s loaded attributes on every commit, and SQLModel's model_dump() only
    # serializes currently-loaded attributes, silently returning `{}` on the next commit.
    with Session(engine, expire_on_commit=False) as session:
        yield session


class DecisionRequest(BaseModel):
    decision: str  # "approved" | "rejected" | "more_investigation_requested"
    reviewer: str
    notes: Optional[str] = None


def _log(session: Session, transaction_id: str, investigation_id: Optional[int], event_type: str, event_data: dict):
    session.add(
        AuditLogEntry(
            transaction_id=transaction_id,
            investigation_id=investigation_id,
            event_type=event_type,
            event_data=event_data,
        )
    )
    session.commit()


@router.post("/{transaction_id}/run")
def run_investigation(
    transaction_id: str, session: Session = Depends(get_session), core_db=Depends(get_core_db)
):
    scored = fetch_and_score(transaction_id, core_db)
    if scored is None:
        raise HTTPException(status_code=404, detail=f"transaction {transaction_id} not found")

    _log(session, transaction_id, None, "model_scored", {
        "risk_score": scored["risk_score"], "anomaly_score": scored["anomaly_score"],
        "above_threshold": scored["above_threshold"],
    })

    if not scored["above_threshold"]:
        raise HTTPException(
            status_code=400,
            detail=f"risk_score {scored['risk_score']:.4f} is below the alert threshold; "
                   f"no investigation warranted",
        )

    _log(session, transaction_id, None, "agent_investigation_started", {})
    try:
        proc = subprocess.run(
            [AGENT_PYTHON_BIN, "-m", "agent.investigate", transaction_id],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=AGENT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Investigation Agent timed out")

    if proc.returncode != 0:
        raise HTTPException(status_code=502, detail=f"Investigation Agent failed: {proc.stderr[-3000:]}")

    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail=f"Investigation Agent returned non-JSON output: {proc.stdout[-2000:]}")

    inv = Investigation(
        transaction_id=transaction_id,
        status=STATUS_PENDING_REVIEW,
        risk_score=scored["risk_score"],
        anomaly_score=scored["anomaly_score"],
        model_version=scored["model_version"],
        report=result.get("report"),
        report_error=result.get("report_error"),
        trace=result.get("trace"),
        num_turns=result.get("num_turns"),
        total_cost_usd=result.get("total_cost_usd"),
        agent_is_error=bool(result.get("is_error")),
    )
    session.add(inv)
    session.commit()
    session.refresh(inv)

    _log(session, transaction_id, inv.id, "agent_investigation_completed", {
        "recommended_action": (result.get("report") or {}).get("recommended_action"),
        "confidence": (result.get("report") or {}).get("confidence"),
        "total_cost_usd": result.get("total_cost_usd"),
    })
    return inv.model_dump()


@router.get("/flagged", response_model=List[Investigation])
def list_flagged(session: Session = Depends(get_session)):
    statement = (
        select(Investigation)
        .where(Investigation.status == STATUS_PENDING_REVIEW)
        .order_by(Investigation.risk_score.desc())
    )
    return session.exec(statement).all()


RISK_BANDS = [
    (0.0, 0.2, "0–20%"),
    (0.2, 0.4, "20–40%"),
    (0.4, 0.6, "40–60%"),
    (0.6, 0.8, "60–80%"),
    (0.8, 1.0, "80–100%"),
]


class RiskBandStats(BaseModel):
    label: str
    min: float
    max: float
    count: int
    by_recommended_action: Dict[str, int]


class InvestigationStats(BaseModel):
    total: int
    by_status: Dict[str, int]
    by_recommended_action: Dict[str, int]
    by_confidence: Dict[str, int]
    risk_score_histogram: List[RiskBandStats]


@router.get("/stats", response_model=InvestigationStats)
def get_stats(session: Session = Depends(get_session)):
    """Aggregate counts for the dashboard — read-only, computed from the
    existing Investigation table, no schema change."""
    rows = session.exec(select(Investigation)).all()

    by_status = Counter(r.status for r in rows)
    by_recommended_action = Counter((r.report or {}).get("recommended_action", "none") for r in rows)
    by_confidence = Counter((r.report or {}).get("confidence", "none") for r in rows)

    histogram = []
    for low, high, label in RISK_BANDS:
        in_band = [
            r for r in rows
            if low <= r.risk_score < high or (high == 1.0 and r.risk_score == 1.0)
        ]
        band_actions = Counter((r.report or {}).get("recommended_action", "none") for r in in_band)
        histogram.append(
            RiskBandStats(
                label=label,
                min=low,
                max=high,
                count=len(in_band),
                by_recommended_action=dict(band_actions),
            )
        )

    return InvestigationStats(
        total=len(rows),
        by_status=dict(by_status),
        by_recommended_action=dict(by_recommended_action),
        by_confidence=dict(by_confidence),
        risk_score_histogram=histogram,
    )


@router.get("/{investigation_id}", response_model=Investigation)
def get_investigation(investigation_id: int, session: Session = Depends(get_session)):
    inv = session.get(Investigation, investigation_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="investigation not found")
    return inv


@router.post("/{investigation_id}/decision")
def submit_decision(investigation_id: int, body: DecisionRequest, session: Session = Depends(get_session)):
    inv = session.get(Investigation, investigation_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="investigation not found")
    if body.decision not in VALID_DECISIONS:
        raise HTTPException(status_code=422, detail=f"decision must be one of {sorted(VALID_DECISIONS)}")

    inv.status = body.decision
    inv.decided_at = datetime.utcnow()
    inv.decided_by = body.reviewer
    inv.decision_notes = body.notes
    session.add(inv)
    session.commit()
    session.refresh(inv)

    _log(session, inv.transaction_id, inv.id, "human_decision", {
        "decision": body.decision, "reviewer": body.reviewer, "notes": body.notes,
    })
    return inv.model_dump()


@router.get("/{investigation_id}/audit-log")
def get_audit_log(investigation_id: int, session: Session = Depends(get_session)):
    statement = (
        select(AuditLogEntry)
        .where(AuditLogEntry.investigation_id == investigation_id)
        .order_by(AuditLogEntry.created_at)
    )
    return session.exec(statement).all()
