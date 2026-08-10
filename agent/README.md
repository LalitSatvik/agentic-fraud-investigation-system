# agent/

The investigation agent: given a flagged transaction, gathers evidence and produces a
structured report with a recommended action. It has no authority to act on that
recommendation — see `api/` for the human-in-the-loop gate.

## Contents

- `investigate.py` — orchestration. Runs an agent session scoped to exactly four tools (no
  shell or filesystem access), with the final report constrained to the JSON schema in
  `report_schema.py` rather than parsed out of free text.
- `system_prompt.py` — the agent's instructions: investigation method, evidentiary standards
  (state only what a tool result or the transaction data actually showed), and how to weigh
  conflicting evidence.
- `report_schema.py` — the structured output contract (summary, risk factors with cited
  evidence, mitigating factors, confidence, recommended action, rationale).
- `tools/enrichment_tools.py` — the four tools, implemented as thin HTTP clients against the
  API's internal enrichment endpoints (`api/routes/enrichment.py`):
  - `geo_ip_lookup` — IP/device/geolocation evidence, including an impossible-travel check
    against the customer's previous transaction
  - `customer_history` — profile and prior-transaction history, computed causally (only
    transactions before the one under review)
  - `graph_features` — accounts linked by shared device or IP, and their own fraud track record
  - `reputation_check` — counterparty category risk, watchlist status, and history

## Why tools call an internal API instead of querying data directly

Each tool's request/response shape matches what an equivalent real service would return (an IP
intelligence API, a sanctions-list API, a graph database) so a real one can be substituted later
by changing the tool implementation, not the agent's reasoning or prompt.
