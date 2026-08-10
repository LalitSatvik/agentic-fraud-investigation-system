"""
The human-in-the-loop core: an Investigation is created once the Investigation
Agent finishes (status starts at "pending_review") and stays there — nothing
downstream treats the agent's recommendation as final — until a human posts a
decision via POST /investigations/{id}/decision. Every state change is also
mirrored into AuditLogEntry as an append-only trail.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

# Terminal/working states for Investigation.status
STATUS_PENDING_REVIEW = "pending_review"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_MORE_INVESTIGATION_REQUESTED = "more_investigation_requested"


class Investigation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_id: str = Field(index=True)

    status: str = Field(default=STATUS_PENDING_REVIEW, index=True)

    # Model scoring, captured at investigation time
    risk_score: float
    anomaly_score: float
    model_version: str

    # Agent output
    report: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    report_error: Optional[str] = None
    trace: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    num_turns: Optional[int] = None
    total_cost_usd: Optional[float] = None
    agent_is_error: bool = False

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Human decision
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = None
    decision_notes: Optional[str] = None


class AuditLogEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_id: str = Field(index=True)
    investigation_id: Optional[int] = Field(default=None, index=True)
    event_type: str = Field(index=True)
    event_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
