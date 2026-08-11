"""
Investigation agent orchestration. Given a transaction (and its risk score),
runs an agent session with the four read-only enrichment tools.

Supports multiple LLM backends:
1. Anthropic (if ANTHROPIC_API_KEY is set)
2. Groq (if GROQ_API_KEY is set) - Free tier: https://console.groq.com/keys
3. Gemini (if GEMINI_API_KEY is set) - Free tier: https://aistudio.google.com/app/apikey
4. OpenAI (if OPENAI_API_KEY is set)
5. Fallback Mock Mode (if no API key set or MOCK_AGENT=true) - Zero cost, rule-based reasoning over real DB data.

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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agent.report_schema import InvestigationReport  # noqa: E402
from agent.system_prompt import SYSTEM_PROMPT  # noqa: E402

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
MAX_TURNS = 20

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "geo_ip_lookup",
            "description": "Look up IP address, device, and geolocation evidence for a transaction, including an impossible-travel check.",
            "parameters": {
                "type": "object",
                "properties": {"transaction_id": {"type": "string"}},
                "required": ["transaction_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "customer_history",
            "description": "Fetch customer profile, account age, risk segment, prior fraud history, and transaction velocity.",
            "parameters": {
                "type": "object",
                "properties": {"transaction_id": {"type": "string"}},
                "required": ["transaction_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "graph_features",
            "description": "Find accounts linked to this customer via shared device or IP address and their fraud rates.",
            "parameters": {
                "type": "object",
                "properties": {"transaction_id": {"type": "string"}},
                "required": ["transaction_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reputation_check",
            "description": "Check counterparty category risk, sanctions watchlist status, and historical fraud rate.",
            "parameters": {
                "type": "object",
                "properties": {"transaction_id": {"type": "string"}},
                "required": ["transaction_id"],
            },
        },
    },
]


async def fetch_transaction(transaction_id: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
        resp = await client.get(f"/internal/transactions/{transaction_id}")
        resp.raise_for_status()
        return resp.json()


async def execute_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    tx_id = args.get("transaction_id", "")
    endpoint_map = {
        "geo_ip_lookup": f"/internal/enrichment/geo-ip/{tx_id}",
        "customer_history": f"/internal/enrichment/customer-history/{tx_id}",
        "graph_features": f"/internal/enrichment/graph/{tx_id}",
        "reputation_check": f"/internal/enrichment/reputation/{tx_id}",
    }
    path = endpoint_map.get(name)
    if not path:
        return {"error": f"Unknown tool: {name}"}

    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
        try:
            resp = await client.get(path)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}


async def investigate_claude(transaction: Dict[str, Any]) -> Dict[str, Any]:
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
    from agent.tools.enrichment_tools import ALL_TOOLS

    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
    server = create_sdk_mcp_server(name="fraud_tools", version="1.0.0", tools=ALL_TOOLS)
    options = ClaudeAgentOptions(
        tools=[],
        mcp_servers={"fraud_tools": server},
        permission_mode="bypassPermissions",
        system_prompt=SYSTEM_PROMPT,
        model=model,
        max_turns=MAX_TURNS,
        output_format=InvestigationReport.json_schema_for_sdk(),
    )
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
        except Exception as e:
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


async def investigate_openai_format(
    transaction: Dict[str, Any], api_key: str, endpoint: str, model_name: str
) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    tx_id = transaction["transaction_id"]
    schema_str = json.dumps(InvestigationReport.model_json_schema(), indent=2)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + f"\n\nReturn your final output strictly as JSON matching this JSON schema:\n{schema_str}"},
        {
            "role": "user",
            "content": f"Investigate this flagged transaction and produce your report.\n\nTransaction under review:\n{json.dumps(transaction, indent=2, default=str)}",
        },
    ]

    trace: List[Dict[str, Any]] = []
    turns = 0
    report = None
    report_error = None

    async with httpx.AsyncClient(timeout=45.0) as client:
        while turns < MAX_TURNS:
            turns += 1
            payload = {
                "model": model_name,
                "messages": messages,
                "tools": OPENAI_TOOLS,
                "tool_choice": "auto",
            }
            resp = await client.post(endpoint, headers=headers, json=payload)
            if resp.status_code != 200:
                report_error = f"API call failed ({resp.status_code}): {resp.text[:500]}"
                print(f"[LLM API Error] {report_error}. Falling back to mock investigation.")
                return await investigate_mock(transaction)

            data = resp.json()
            choice = data["choices"][0]
            msg = choice["message"]

            # Construct clean assistant message (convert null content to empty string for Groq/OpenAI compat)
            assistant_msg = {
                "role": "assistant",
                "content": msg.get("content") or "",
            }
            if msg.get("tool_calls"):
                assistant_msg["tool_calls"] = msg["tool_calls"]
            messages.append(assistant_msg)

            if msg.get("content"):
                trace.append({"role": "assistant", "type": "text", "text": msg["content"]})
                # Attempt to parse final structured report if present
                try:
                    raw_text = msg["content"].strip()
                    if raw_text.startswith("```json"):
                        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in raw_text:
                        raw_text = raw_text.split("```")[1].split("```")[0].strip()
                    parsed = json.loads(raw_text)
                    if isinstance(parsed, dict) and "recommended_action" in parsed:
                        report = InvestigationReport.model_validate(parsed).model_dump()
                        break
                except Exception:
                    pass

            tool_calls = msg.get("tool_calls", [])
            if not tool_calls:
                break

            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                try:
                    fn_args = json.loads(tc["function"]["arguments"])
                except Exception:
                    fn_args = {"transaction_id": tx_id}

                trace.append({"role": "assistant", "type": "tool_call", "tool": fn_name, "input": fn_args})
                res_data = await execute_tool(fn_name, fn_args)
                trace.append(
                    {
                        "role": "tool",
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": json.dumps(res_data),
                        "is_error": "error" in res_data,
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(res_data),
                    }
                )

    if not report and not report_error:
        # If model ended without valid JSON, request JSON final formatting
        messages.append(
            {
                "role": "user",
                "content": f"Please output your final InvestigationReport now as a raw JSON object matching schema:\n{schema_str}",
            }
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(endpoint, headers=headers, json={"model": model_name, "messages": messages})
            if resp.status_code == 200:
                raw_text = resp.json()["choices"][0]["message"]["content"].strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                try:
                    parsed = json.loads(raw_text)
                    report = InvestigationReport.model_validate(parsed).model_dump()
                except Exception as e:
                    report_error = f"Failed to parse report JSON: {e}"

    return {
        "transaction_id": tx_id,
        "report": report,
        "report_error": report_error,
        "trace": trace,
        "num_turns": turns,
        "total_cost_usd": 0.0,
        "is_error": report is None,
        "stop_reason": "end_turn" if report else "error",
    }


async def investigate_mock(transaction: Dict[str, Any]) -> Dict[str, Any]:
    tx_id = transaction["transaction_id"]
    risk_score = transaction.get("risk_score", 0.8)

    geo_data = await execute_tool("geo_ip_lookup", {"transaction_id": tx_id})
    cust_data = await execute_tool("customer_history", {"transaction_id": tx_id})
    graph_data = await execute_tool("graph_features", {"transaction_id": tx_id})
    rep_data = await execute_tool("reputation_check", {"transaction_id": tx_id})

    trace = [
        {"role": "assistant", "type": "tool_call", "tool": "geo_ip_lookup", "input": {"transaction_id": tx_id}},
        {"role": "tool", "type": "tool_result", "tool_use_id": "call_geo", "content": json.dumps(geo_data), "is_error": False},
        {"role": "assistant", "type": "tool_call", "tool": "customer_history", "input": {"transaction_id": tx_id}},
        {"role": "tool", "type": "tool_result", "tool_use_id": "call_cust", "content": json.dumps(cust_data), "is_error": False},
        {"role": "assistant", "type": "tool_call", "tool": "graph_features", "input": {"transaction_id": tx_id}},
        {"role": "tool", "type": "tool_result", "tool_use_id": "call_graph", "content": json.dumps(graph_data), "is_error": False},
        {"role": "assistant", "type": "tool_call", "tool": "reputation_check", "input": {"transaction_id": tx_id}},
        {"role": "tool", "type": "tool_result", "tool_use_id": "call_rep", "content": json.dumps(rep_data), "is_error": False},
    ]

    risk_factors = []
    mitigating_factors = []

    # Geo IP signals
    if geo_data.get("impossible_travel"):
        risk_factors.append({
            "factor": "Impossible Travel Flagged",
            "evidence": f"Distance between transactions suggests impossible speed ({geo_data.get('speed_kmh', 0):.0f} km/h).",
            "severity": "high",
        })
    elif geo_data.get("is_new_device"):
        risk_factors.append({
            "factor": "Unrecognized Device",
            "evidence": f"Transaction initiated from new device fingerprint in {geo_data.get('geo_city', 'unknown location')}.",
            "severity": "medium",
        })

    # Graph signals
    linked_accounts = graph_data.get("linked_accounts", [])
    high_risk_links = [a for a in linked_accounts if a.get("confirmed_fraud_count", 0) > 0 or a.get("fraud_rate", 0) > 0.3]
    if high_risk_links:
        risk_factors.append({
            "factor": "Shared Infrastructure Fraud Ring Link",
            "evidence": f"Customer linked via shared IP/device to {len(high_risk_links)} accounts with confirmed fraud histories.",
            "severity": "high",
        })

    # Reputation signals
    counterparty_risk = rep_data.get("counterparty_risk_category", "normal")
    if counterparty_risk in ["high", "critical"] or rep_data.get("on_watchlist"):
        risk_factors.append({
            "factor": "High Risk Counterparty Destination",
            "evidence": f"Counterparty {rep_data.get('counterparty_id')} categorized as '{counterparty_risk}' risk.",
            "severity": "high",
        })

    # Customer history signals
    tenure_days = cust_data.get("account_age_days", 0)
    prior_fraud = cust_data.get("prior_confirmed_fraud_count", 0)
    if prior_fraud > 0:
        risk_factors.append({
            "factor": "Prior Confirmed Fraud History",
            "evidence": f"Customer account has {prior_fraud} prior confirmed fraud events on record.",
            "severity": "high",
        })
    elif tenure_days > 180 and len(risk_factors) == 0:
        mitigating_factors.append(f"Long-standing account history ({tenure_days} days) with zero prior fraud events.")

    if not risk_factors:
        risk_factors.append({
            "factor": "Elevated Model Score Threshold",
            "evidence": f"Initial XGBoost scoring flagged transaction with risk score {risk_score:.2f}.",
            "severity": "medium",
        })

    if any(rf["severity"] == "high" for rf in risk_factors) or risk_score >= 0.85:
        action = "deny"
        confidence = "high"
        rationale = "Multiple high-severity risk indicators identified across graph connection, device, or counterparty history."
    elif len(risk_factors) > 1:
        action = "escalate"
        confidence = "medium"
        rationale = "Elevated risk signals detected. Requires senior human review for final policy determination."
    else:
        action = "approve"
        confidence = "high"
        rationale = "Investigation revealed no high-risk signals; customer profile and transaction context are consistent with legitimate behavior."

    report = InvestigationReport(
        transaction_id=tx_id,
        summary=f"Automated investigation for transaction {tx_id} (Risk score: {risk_score:.2f}). Evaluated 4 enrichment signals.",
        risk_factors=risk_factors,
        mitigating_factors=mitigating_factors,
        tools_consulted=["geo_ip_lookup", "customer_history", "graph_features", "reputation_check"],
        confidence=confidence,
        recommended_action=action,
        rationale=rationale,
    ).model_dump()

    return {
        "transaction_id": tx_id,
        "report": report,
        "report_error": None,
        "trace": trace,
        "num_turns": 4,
        "total_cost_usd": 0.0,
        "is_error": False,
        "stop_reason": "end_turn",
    }


async def investigate(transaction: Dict[str, Any]) -> Dict[str, Any]:
    if os.environ.get("GROQ_API_KEY"):
        api_key = os.environ["GROQ_API_KEY"]
        model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        endpoint = "https://api.groq.com/openai/v1/chat/completions"
        return await investigate_openai_format(transaction, api_key, endpoint, model)

    if os.environ.get("GEMINI_API_KEY"):
        api_key = os.environ["GEMINI_API_KEY"]
        model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        endpoint = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        return await investigate_openai_format(transaction, api_key, endpoint, model)

    if os.environ.get("OPENAI_API_KEY"):
        api_key = os.environ["OPENAI_API_KEY"]
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        endpoint = "https://api.openai.com/v1/chat/completions"
        return await investigate_openai_format(transaction, api_key, endpoint, model)

    if os.environ.get("ANTHROPIC_API_KEY"):
        return await investigate_claude(transaction)

    # Fallback if no key is set or MOCK_AGENT=true
    return await investigate_mock(transaction)


async def investigate_transaction_id(transaction_id: str) -> Dict[str, Any]:
    transaction = await fetch_transaction(transaction_id)
    return await investigate(transaction)


def investigate_sync(transaction: Dict[str, Any]) -> Dict[str, Any]:
    return asyncio.run(investigate(transaction))


if __name__ == "__main__":
    txn_id = sys.argv[1] if len(sys.argv) > 1 else "TXN100033"
    result = asyncio.run(investigate_transaction_id(txn_id))
    print(json.dumps(result, indent=2, default=str))
