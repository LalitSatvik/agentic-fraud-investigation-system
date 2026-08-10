"""Structured output schema for the Investigation Agent's report. Passed to
the Claude Agent SDK as `output_format` (JSON schema), so the final
`ResultMessage.structured_output` is already validated report data rather
than free text to parse.
"""
from typing import List, Literal

from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high"]
Confidence = Literal["low", "medium", "high"]
RecommendedAction = Literal["approve", "deny", "escalate"]


class RiskFactor(BaseModel):
    factor: str = Field(description="Short name of the risk factor, e.g. 'Geo/device mismatch'")
    evidence: str = Field(description="The specific tool finding(s) that support this factor")
    severity: Severity


class InvestigationReport(BaseModel):
    transaction_id: str
    summary: str = Field(description="2-4 sentence plain-English overview of the case")
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    mitigating_factors: List[str] = Field(
        default_factory=list, description="Evidence that argues against fraud, if any"
    )
    tools_consulted: List[str] = Field(default_factory=list)
    confidence: Confidence
    recommended_action: RecommendedAction
    rationale: str = Field(description="How the evidence above leads to the recommended action")

    @classmethod
    def json_schema_for_sdk(cls) -> dict:
        return {"type": "json_schema", "schema": cls.model_json_schema()}
