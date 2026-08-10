"""
Load the processed parquet tables into the project's dev database (SQLite by
default; point DATABASE_URL at Postgres to load there instead — schema is
identical either way).

Tables loaded: customers, transactions, transaction_context, merchants,
graph_edges, customer_ring_labels (ground-truth eval-only, kept separate from
`customers` so agent tools never see it).

Run:
    python data/generators/load_to_db.py
"""
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"
DEFAULT_DB_URL = f"sqlite:///{ROOT / 'dev.db'}"


def main() -> None:
    db_url = os.environ.get("DATABASE_URL", DEFAULT_DB_URL)
    if db_url.startswith("postgresql"):
        db_url = db_url  # used as-is; requires the `deploy` Postgres container to be up
    print(f"Loading into: {db_url}")
    engine = create_engine(db_url)

    customers = pd.read_parquet(PROCESSED_DIR / "customers.parquet")
    ring_labels = customers[["customer_id", "is_known_ring_member"]].copy()
    customers = customers.drop(columns=["is_known_ring_member"])

    transactions = pd.read_parquet(PROCESSED_DIR / "transactions.parquet")
    tx_context = pd.read_parquet(PROCESSED_DIR / "transaction_context.parquet")
    merchants = pd.read_parquet(PROCESSED_DIR / "merchants.parquet")
    graph_edges = pd.read_parquet(PROCESSED_DIR / "graph_edges.parquet")

    tables = {
        "customers": customers,
        "transactions": transactions,
        "transaction_context": tx_context,
        "merchants": merchants,
        "graph_edges": graph_edges,
        "customer_ring_labels": ring_labels,
    }

    with engine.begin() as conn:
        for name, df in tables.items():
            df.to_sql(name, conn, if_exists="replace", index=(name == "graph_edges"), index_label="id" if name == "graph_edges" else None)
            print(f"  {name}: {len(df):,} rows")

        # Helpful indexes for the query patterns the enrichment tools/API will use.
        index_stmts = [
            "CREATE INDEX IF NOT EXISTS ix_transactions_customer_id ON transactions(customer_id)",
            "CREATE INDEX IF NOT EXISTS ix_transactions_counterparty_id ON transactions(counterparty_id)",
            "CREATE INDEX IF NOT EXISTS ix_transactions_is_fraud ON transactions(is_fraud)",
            "CREATE INDEX IF NOT EXISTS ix_tx_context_transaction_id ON transaction_context(transaction_id)",
            "CREATE INDEX IF NOT EXISTS ix_graph_edges_a ON graph_edges(customer_id_a)",
            "CREATE INDEX IF NOT EXISTS ix_graph_edges_b ON graph_edges(customer_id_b)",
        ]
        for stmt in index_stmts:
            try:
                conn.execute(text(stmt))
            except Exception as e:  # pragma: no cover - Postgres syntax differs slightly, non-fatal
                print(f"  (index skipped: {e})")

    print("Done.")


if __name__ == "__main__":
    main()
