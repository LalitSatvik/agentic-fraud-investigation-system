# ml/

The base fraud classifier — the first-pass model that decides which transactions get escalated
to the investigation agent.

## Contents

- `features/build_features.py` — feature engineering. Deliberately limited to transaction-level
  fields and causal customer-history aggregates (transactions strictly before the one being
  scored); the richer enrichment data (geo/IP, device, account graph, merchant reputation) is
  reserved for the investigation agent, mirroring how a real first-pass model and a downstream
  investigation step would typically be scoped differently.
- `training/train_model.py` — trains an XGBoost classifier on a time-ordered split (not a random
  split, to avoid leaking future transactions into training) plus an IsolationForest as an
  unsupervised companion signal. Writes trained artifacts and a model card to `artifacts/`.
- `scoring.py` — the scoring interface used by the API and batch pipeline
  (`FraudScorer.score_transaction`), so callers don't need to know about feature engineering or
  artifact paths.
- `artifacts/` — trained model, chosen operating threshold, metrics, and `model_card.md`
  documenting performance and known limitations (including a dataset-specific artifact worth
  reading before trusting the reported metrics).

## Design note: threshold selection

The operating threshold is chosen on a validation set as the highest threshold that still
clears 85% recall — missing fraud is treated as costlier than a false positive here, since false
positives are reviewed by the investigation agent and a human, not auto-declined.
