# data/

Builds the dataset used by the rest of the system: PaySim transactions plus a synthesized
enrichment layer that gives the investigation agent something real to investigate.

## Why synthesize an enrichment layer

PaySim ships transaction-level fields only (amount, type, balances) and its account
identifiers are essentially one-off — a given `nameOrig` appears in only one transaction in the
vast majority of cases, so there's no real customer history to query. `generators/` builds a
persistent identity layer on top of it:

- **Customers** (`generators/synthesize_enrichment.py`) — a pool of ~18,000 synthetic customer
  profiles, with transactions assigned using a heavy-tailed distribution so repeat-customer
  history actually exists. A small subset ("ring members") is deliberately overrepresented in
  fraud transactions and shares hardware with each other, to give the account-graph tool real
  signal to find.
- **Device/IP/geo context** — per transaction, generated with fraud-correlated probabilities
  (new device, VPN/proxy, distance from home) so the enrichment tools have genuine evidence to
  surface rather than random noise.
- **Merchants** — category, country, and watchlist status per counterparty, skewed toward
  higher-risk categories for counterparties that appear in fraud transactions.
- **Account graph** — edges between customers who share a device or IP address, derived after
  generation.

## Pipeline

```
raw/paysim/*.csv  →  sample_paysim.py  →  processed/transactions_base.parquet
                                          →  synthesize_enrichment.py
                                          →  processed/{transactions,customers,
                                              transaction_context,merchants,graph_edges}.parquet
                                          →  load_to_db.py
                                          →  SQLite/Postgres
```

`processed/*.parquet` is committed to the repository so the rest of the system runs without
needing Kaggle credentials or a regeneration step. See `../docs/DEVELOPMENT.md` to regenerate
from scratch.
