# Development notes

## Environment setup

Two Python environments, split by version requirement:

- **ML/API environment**, Python 3.8+. Used for `data/`, `ml/`, `api/`, and `eval/`'s
  orchestration script. Install with:
  ```bash
  pip install -r requirements-ml-api.txt
  ```
- **Agent environment**, Python 3.10+ required (the investigation agent's SDK enforces this).
  Used only for `agent/` and the LLM-judge scorer in `eval/scorers/`. Install with:
  ```bash
  pip install -r agent/requirements.txt
  ```

The API calls the agent as a subprocess (`api/routes/investigations.py`), passing the target
Python interpreter via the `AGENT_PYTHON_BIN` environment variable, so the two environments never
need to share a process or dependency set. In Docker this split is unnecessary — the image in
`deploy/Dockerfile` runs everything on Python 3.11, and `AGENT_PYTHON_BIN` is set to the same
interpreter used for the API.

`web/` is a standard Node/Vite project — install with `npm install` inside that directory.

## Regenerating the dataset and model from scratch

The repository ships with a pre-built dataset (`data/processed/`) and trained model
(`ml/artifacts/`). To regenerate them:

```bash
# 1. Download PaySim from Kaggle into data/raw/paysim/ (requires Kaggle API credentials)
python data/generators/sample_paysim.py

# 2. Build the synthetic enrichment layer (customer identities, device/geo/IP context,
#    merchant reputation, account graph) on top of the sampled transactions
python data/generators/synthesize_enrichment.py

# 3. Load everything into the local database (dev.db by default)
python data/generators/load_to_db.py

# 4. Feature engineering and model training
python ml/features/build_features.py
python ml/training/train_model.py
```

## Conventions

- Enrichment tool functions in `agent/tools/` keep the same interface a real MCP server
  (IPinfo, AbuseIPDB, a graph database) would expose, even though they currently read from the
  synthesized dataset — swapping in a real data source later is a configuration change, not a
  rewrite.
- Every model score, tool call, agent recommendation, and human decision is written to an
  append-only audit log (`api/models/investigation.py::AuditLogEntry`).
- `must_not_recommend` in the gold-standard eval cases marks a specific failure mode to check
  for (e.g. a false positive on a case with surface-level red flags but no real signal), not
  just a single expected answer.
