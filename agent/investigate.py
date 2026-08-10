"""
Investigation agent orchestration. Given a transaction (and its risk score),
runs an agent session with only the four read-only enrichment tools
available (no shell or filesystem access at all — `tools=[]` disables the
SDK's default toolset), and returns a structured InvestigationReport plus
the full message trace for audit/eval purposes.

The agent has no authority to act — its output is a recommendation. The
human-in-the-loop gate lives in the API layer: a report is persisted as
"pending_review" and only a human decision moves it further.

Run standalone:
    python -m agent.investigate TXN100033
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    create_sdk_mcp_server,
    query,
)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agent.report_schema import InvestigationReport  # noqa: E402
from agent.system_prompt import SYSTEM_PROMPT  # noqa: E402
from agent.tools.enrichment_tools import ALL_TOOLS  # noqa: E402

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
MAX_TURNS = 20


async def fetch_transaction(transaction_id: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
        resp = await client.get(f"/internal/transactions/{transaction_id}")
        resp.raise_for_status()
        return resp.json()


def build_options() -> ClaudeAgentOptions:
    server = create_sdk_mcp_server(name="fraud_tools", version="1.0.0", tools=ALL_TOOLS)
    return ClaudeAgentOptions(
        tools=[],  # disable every default tool (shell, file read/write, web fetch, ...)
        mcp_servers={"fraud_tools": server},
        permission_mode="bypassPermissions",  # only the 4 read-only fraud tools exist at all
        system_prompt=SYSTEM_PROMPT,
        model=MODEL,
        max_turns=MAX_TURNS,
        output_format=InvestigationReport.json_schema_for_sdk(),
    )


async def investigate(transaction: Dict[str, Any]) -> Dict[str, Any]:
    """transaction: the dict returned by GET /internal/transactions/{id} (includes risk_score)."""
    options = build_options()
    prompt = (
        "Investigate this flagged transaction and produce your report.\n\n"
        f"Transaction under review:\n{json.dumps(transaction, indent=2, default=str)}"
    )

    trace: List[Dict[str, Any]] = []
    result_message: Optional[ResultMessage] = None

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    trace.append({"role": "assistant", "type": "text", "text": block.text})
                elif isinstance(block, ToolUseBlock):
                    trace.append(
                        {"role": "assistant", "type": "tool_call", "tool": block.name, "input": block.input}
                    )
                elif isinstance(block, ThinkingBlock):
                    trace.append({"role": "assistant", "type": "thinking", "text": block.thinking})
        elif isinstance(message, UserMessage) and isinstance(message.content, list):
            for block in message.content:
                if isinstance(block, ToolResultBlock):
                    trace.append(
                        {
                            "role": "tool",
                            "type": "tool_result",
                            "tool_use_id": block.tool_use_id,
                            "content": block.content,
                            "is_error": block.is_error,
                        }
                    )
        elif isinstance(message, ResultMessage):
            result_message = message

    report = None
    report_error = None
    if result_message and result_message.structured_output:
        try:
            report = InvestigationReport.model_validate(result_message.structured_output).model_dump()
        except Exception as e:  # schema mismatch — surface, don't silently drop
            report_error = str(e)

    return {
        "transaction_id": transaction["transaction_id"],
        "report": report,
        "report_error": report_error,
        "trace": trace,
        "num_turns": result_message.num_turns if result_message else None,
        "total_cost_usd": result_message.total_cost_usd if result_message else None,
        "is_error": result_message.is_error if result_message else True,
        "stop_reason": result_message.stop_reason if result_message else None,
    }


async def investigate_transaction_id(transaction_id: str) -> Dict[str, Any]:
    transaction = await fetch_transaction(transaction_id)
    return await investigate(transaction)


def investigate_sync(transaction: Dict[str, Any]) -> Dict[str, Any]:
    return asyncio.run(investigate(transaction))


if __name__ == "__main__":
    txn_id = sys.argv[1] if len(sys.argv) > 1 else "TXN100033"
    result = asyncio.run(investigate_transaction_id(txn_id))
    print(json.dumps(result, indent=2, default=str))
