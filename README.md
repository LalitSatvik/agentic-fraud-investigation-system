# Agentic Fraud Investigation System

A fraud detection pipeline that goes beyond a bare risk score. A classical model (XGBoost, with
an IsolationForest anomaly signal) scores incoming transactions; anything above threshold is
handed to an LLM-based investigation agent that pulls supporting evidence — IP/device
geolocation, customer transaction history, shared-device/IP account networks, counterparty
reputation — reasons over it, and writes a structured report with a recommended action. A human
reviewer approves, rejects, or sends the case back for further investigation; the agent has no
authority to act on its own. A gold-standard evaluation harness scores report quality against
curated cases.

## Architecture

```
PaySim transactions + synthesized enrichment (customers, devices, geo/IP, merchants, graph)
        │
        ▼
XGBoost classifier → risk_score                                              ml/
        │  (above threshold)
        ▼
Investigation agent                                                          agent/
  ├── geo_ip_lookup       — IP/device/geo + impossible-travel check
  ├── customer_history    — profile + causal prior-transaction history
  ├── graph_features      — shared-device/IP account network + fraud rates
  └── reputation_check    — counterparty category risk + watchlist + history
        │
        ▼
API: review queue, investigation reports, decisions, audit log               api/
        │
        ▼
Reviewer dashboard (approve / reject / request more investigation)           web/
        │
        ▼
Evaluation harness: gold-standard cases scored by an LLM rubric judge        eval/
```

## Repository layout

| Path | Contents |
|---|---|
| `data/` | PaySim ingestion, synthetic enrichment generators, processed datasets |
| `ml/` | Feature engineering, model training, scoring interface, trained artifacts |
| `agent/` | Investigation agent: tool implementations, report schema, orchestration |
| `api/` | FastAPI backend: enrichment endpoints, transaction scoring, review queue, audit log |
| `web/` | Reviewer dashboard (React, TypeScript, Tailwind) |
| `eval/` | Gold-standard case set and LLM-judge scoring harness |
| `pipeline/` | Batch runner that scores transactions and triggers investigations |
| `deploy/` | Docker Compose reference deployment |
| `docs/` | Development notes (environment setup, conventions) |

Each of these has its own `README.md` with more detail.

## Environments

Python dependencies are split across two environments because the investigation agent's SDK
requires Python 3.10+, while the rest of the stack targets 3.8 for compatibility with an existing
environment:

- **ML/API environment** (Python 3.8+) — `data/`, `ml/`, `api/`, `eval/`'s orchestration.
  Dependencies: `requirements-ml-api.txt`.
- **Agent environment** (Python 3.11+) — `agent/` and the eval judge. Dependencies:
  `agent/requirements.txt`.

The API invokes the agent as a subprocess rather than importing it directly, so the two
environments never need to share a process. In the Docker deployment this split doesn't apply —
one image runs everything.

See `docs/DEVELOPMENT.md` for full setup notes.

## Running it locally

Data and trained model artifacts are included in the repository, so the API can be started
without any generation step.

**1. Install dependencies:**
```bash
conda create -n fraud-ml python=3.8 -y && conda run -n fraud-ml pip install -r requirements-ml-api.txt
conda create -n fraud-agent python=3.11 -y && conda run -n fraud-agent pip install -r agent/requirements.txt
```

**2. Load the dataset into a local database:**
```bash
conda run -n fraud-ml python data/generators/load_to_db.py
```

**3. Start the API** (requires `ANTHROPIC_API_KEY`, and `AGENT_PYTHON_BIN` pointing at the
agent environment's interpreter, since the API invokes the agent as a subprocess):
```bash
export ANTHROPIC_API_KEY=sk-...
export AGENT_PYTHON_BIN=$(conda run -n fraud-agent which python)
conda run -n fraud-ml uvicorn api.main:app --reload --port 8000
```

**4. Start the reviewer dashboard:**
```bash
cd web && npm install && npm run dev
```
Open http://localhost:5173. Enter a transaction ID (see `eval/gold_set/gold_set.json` for
examples) to run an investigation, or populate the queue with a batch:
```bash
conda run -n fraud-ml python pipeline/run_batch.py --num 20
```

**5. Evaluate the agent against the gold-standard set** (each case costs one investigation and
one judge call; use `--limit`/`--categories` to control scope):
```bash
conda run -n fraud-agent python eval/run_eval.py --limit 5
```

To regenerate the dataset and model from scratch instead of using the included artifacts, see
`docs/DEVELOPMENT.md`.

## Docker

```bash
ANTHROPIC_API_KEY=sk-... docker compose -f deploy/docker-compose.yml up --build
```
Brings up Postgres, seeds it from the included dataset, and starts the API and dashboard. Not
yet exercised in CI — validate locally before relying on it.

## Known limitations

- **PaySim balance-consistency leakage**: the base classifier's near-perfect test metrics
  (PR-AUC 0.9999) stem from a documented quirk in how PaySim's simulator handles balances on
  fraudulent transfers, not a realistic production result. See `ml/artifacts/model_card.md` for
  the full analysis, including why risk scores cluster into discrete values rather than a smooth
  distribution.
- **Synchronous investigation**: `POST /investigations/{id}/run` blocks for the duration of the
  agent's investigation (20–40s). A production deployment would move this to a background queue.
- **Docker Compose is unverified** end-to-end.
- Enrichment tools query the synthesized dataset through a custom internal API rather than real
  third-party services (IP intelligence, sanctions lists). Each tool's interface is kept
  consistent with what an equivalent real service would return, so swapping one in is a
  configuration change rather than a rewrite — see `agent/README.md`.
