"""
The Investigation Agent's four enrichment tools. Each is a thin HTTP client
against the FastAPI internal enrichment endpoints (api/routes/enrichment.py)
— kept intentionally dumb (fetch + forward as JSON) so all the actual
investigative reasoning happens in the agent's own reasoning, not hidden in
tool logic. Swapping any of these for a real MCP server (IPinfo, AbuseIPDB,
a graph DB) later just means pointing the same shape of call at a different
backend.
"""
import json
import os
from typing import Any, Dict

import httpx

from claude_agent_sdk import tool

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


async def _get(path: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
        resp = await client.get(path)
        resp.raise_for_status()
        return resp.json()


def _text_result(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(data, indent=2)}]}


def _error_result(exc: Exception) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": f"Tool error: {exc}"}], "is_error": True}


@tool(
    "geo_ip_lookup",
    "Look up IP address, device, and geolocation evidence for a transaction, including a "
    "physical-plausibility (impossible-travel) check against the customer's previous "
    "transaction. Use this to check whether the transaction's network/device origin is "
    "consistent with the customer's usual pattern.",
    {"transaction_id": str},
)
async def geo_ip_lookup(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        data = await _get(f"/internal/enrichment/geo-ip/{args['transaction_id']}")
        return _text_result(data)
    except httpx.HTTPStatusError as e:
        return _error_result(e)


@tool(
    "customer_history",
    "Fetch the customer's profile and prior transaction history (as of, i.e. strictly before, "
    "this transaction) — account age, risk segment, prior confirmed fraud, recent transaction "
    "amounts/types, and 7-day velocity. Use this to judge whether the transaction fits the "
    "customer's established behavior.",
    {"transaction_id": str},
)
async def customer_history(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        data = await _get(f"/internal/enrichment/customer-history/{args['transaction_id']}")
        return _text_result(data)
    except httpx.HTTPStatusError as e:
        return _error_result(e)


@tool(
    "graph_features",
    "Find accounts linked to this transaction's customer via a shared device or shared IP "
    "address, and each linked account's own confirmed-fraud track record. Use this to detect "
    "fraud rings / mule-account networks — a customer linked to several high-fraud-rate "
    "accounts is a strong signal even if this specific transaction looks unremarkable alone.",
    {"transaction_id": str},
)
async def graph_features(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        data = await _get(f"/internal/enrichment/graph/{args['transaction_id']}")
        return _text_result(data)
    except httpx.HTTPStatusError as e:
        return _error_result(e)


@tool(
    "reputation_check",
    "Check the counterparty (merchant or transfer recipient)'s category risk, sanctions "
    "watchlist status, and its own historical fraud-involvement rate (as of, i.e. strictly "
    "before, this transaction). Use this to judge whether the money is moving toward a "
    "known-risky destination.",
    {"transaction_id": str},
)
async def reputation_check(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        data = await _get(f"/internal/enrichment/reputation/{args['transaction_id']}")
        return _text_result(data)
    except httpx.HTTPStatusError as e:
        return _error_result(e)


ALL_TOOLS = [geo_ip_lookup, customer_history, graph_features, reputation_check]
