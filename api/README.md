# api/

FastAPI backend: transaction scoring, enrichment data for the investigation agent, the review
queue, and an append-only audit log.

## Contents

- `main.py` — app entrypoint and router registration.
- `db.py` — database engine (SQLite by default; set `DATABASE_URL` for Postgres).
- `routes/transactions.py` — transaction lookup and on-demand scoring
  (`GET /internal/transactions/{id}`).
- `routes/enrichment.py` — the four internal endpoints the agent's tools call
  (`GET /internal/enrichment/{geo-ip,customer-history,graph,reputation}/{transaction_id}`).
- `routes/investigations.py` — the review queue and human-in-the-loop lifecycle:
  - `POST /investigations/{transaction_id}/run` — score the transaction and, if above
    threshold, run the investigation agent (as a subprocess — see `docs/DEVELOPMENT.md`)
  - `GET /investigations/flagged` — the review queue, sorted by risk score
  - `GET /investigations/{id}` — full report and evidence trace
  - `POST /investigations/{id}/decision` — record a human decision
    (`approved` / `rejected` / `more_investigation_requested`)
- `models/investigation.py` — the `Investigation` and `AuditLogEntry` tables. Every model score,
  tool call, agent recommendation, and human decision is written to the audit log.

## Human-in-the-loop by construction

An investigation is created with `status = pending_review` and nothing downstream treats the
agent's recommendation as final. The only way a case leaves `pending_review` is a human posting
a decision — the agent's tools are all read-only, and it has no endpoint through which to act on
a transaction directly.
