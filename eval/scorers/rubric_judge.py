"""
LLM-as-judge rubric scorer. Grades one Investigation Agent report against a
gold-standard case using a single non-agentic Claude call (no tools, no
enrichment access) with structured output — deliberately separate from the
investigation agent itself so grading isn't circularly influenced by the
same tool-calling context, and can't just "trust" the agent's own framing.

Recommendation-correctness itself is scored deterministically elsewhere
(eval/run_eval.py, a plain set-membership check) — this judge is for the
harder-to-automate quality dimensions: evidence completeness, reasoning
quality, and hallucination.
"""
import asyncio
import json
import os
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

Quality = Literal["poor", "adequate", "good", "excellent"]

JUDGE_SYSTEM_PROMPT = """\
You are grading a junior fraud analyst's (an AI agent's) investigation report against a \
gold-standard case definition, for an evaluation harness. You are NOT deciding whether the \
transaction is fraud yourself — you are grading the QUALITY of the report: did it use its \
tools well, is the reasoning sound and specific (not vague or generic), does every risk factor \
cite real evidence from the tool results shown to you, and did it invent any facts not \
supported by those tool outputs?

Score honestly and critically. A report that reaches a defensible conclusion via lazy or \
unsupported reasoning should NOT score "excellent" on reasoning_quality just because the final \
action happened to match expectations. Conversely, a well-reasoned report that is transparent \
about uncertainty should not be penalized for recommending "escalate".
"""


class RubricScore(BaseModel):
    evidence_completeness: Quality = Field(description="Did the report use/cite the evidence available to it")
    reasoning_quality: Quality = Field(description="Is the reasoning specific, coherent, and well-supported")
    hallucination_detected: bool = Field(description="Does the report state any fact not present in the tool outputs")
    hallucination_notes: Optional[str] = None
    overall_score: int = Field(ge=1, le=5, description="1=poor report, 5=excellent report")
    judge_notes: str

    @classmethod
    def json_schema_for_sdk(cls) -> dict:
        return {"type": "json_schema", "schema": cls.model_json_schema()}


def _tool_call_summary(trace: List[Dict[str, Any]]) -> str:
    lines = []
    for entry in trace:
        if entry.get("type") == "tool_call" and entry.get("tool") not in (None, "StructuredOutput"):
            lines.append(f"- called {entry['tool']}")
        elif entry.get("type") == "tool_result":
            content = entry.get("content")
            text = content[0]["text"] if isinstance(content, list) and content and "text" in content[0] else str(content)
            lines.append(f"  result: {text[:600]}")
    return "\n".join(lines) if lines else "(no tools called)"


async def _grade_async(gold_case: Dict[str, Any], report: Dict[str, Any], trace: List[Dict[str, Any]]) -> Dict[str, Any]:
    options = ClaudeAgentOptions(
        tools=[],
        permission_mode="bypassPermissions",
        system_prompt=JUDGE_SYSTEM_PROMPT,
        model=MODEL,
        max_turns=1,
        output_format=RubricScore.json_schema_for_sdk(),
    )
    prompt = f"""\
Gold-standard case definition:
{json.dumps(gold_case, indent=2)}

Evidence the agent actually gathered (tool calls + results):
{_tool_call_summary(trace)}

The agent's final report:
{json.dumps(report, indent=2)}

Grade this report.
"""
    result_message = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result_message = message

    if result_message and result_message.structured_output:
        return RubricScore.model_validate(result_message.structured_output).model_dump()
    return {
        "error": "judge produced no structured output",
        "raw_result": result_message.result if result_message else None,
    }


def grade(gold_case: Dict[str, Any], report: Dict[str, Any], trace: List[Dict[str, Any]]) -> Dict[str, Any]:
    return asyncio.run(_grade_async(gold_case, report, trace))
