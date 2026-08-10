"""
Synthesize the enrichment layer around the sampled PaySim transactions:
persistent customer identities (with realistic repeat-transaction behavior,
which PaySim's own account IDs don't have), per-transaction device/IP/geo
context, a counterparty/merchant table, and a graph-edge table of accounts
that share hardware or network identifiers.

Signal is deliberately injected: fraud rows get elevated odds of a new
device, a geo/home mismatch, VPN/proxy usage, and involvement of a small
"ring" subset of customers who share devices with each other — so the
downstream enrichment tools have real evidence to surface instead of
random noise.

Input:  data/processed/transactions_base.parquet
Output: data/processed/{transactions, customers, transaction_context,
                        merchants, graph_edges}.parquet

Run:
    python data/generators/synthesize_enrichment.py
"""
import argparse
import math
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

from geo_reference import (
    BROWSERS,
    COMMON,
    CONSUMER_ISPS,
    DEVICE_TYPES,
    ELEVATED,
    HOSTING_ISPS,
    MERCHANT_CATEGORIES,
    OS_BY_DEVICE,
    TODAY,
)

PROCESSED_DIR = Path(__file__).resolve().parents[1] / "processed"

fake = Faker()
Faker.seed(42)


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def make_device_id(rng):
    return f"DEV{rng.integers(10_000_000, 99_999_999)}"


def make_ip(rng):
    return f"{rng.integers(1, 224)}.{rng.integers(0, 256)}.{rng.integers(0, 256)}.{rng.integers(1, 255)}"


def build_customers(n_customers: int, n_ring: int, rng: np.random.Generator) -> pd.DataFrame:
    ring_ids = set(rng.choice(n_customers, size=n_ring, replace=False))
    # A small pool of shared devices that ring members draw from, so several
    # ring customers end up on the same hardware -> graph edges.
    ring_device_pool = [make_device_id(rng) for _ in range(max(8, n_ring // 6))]

    rows = []
    for i in range(n_customers):
        customer_id = f"CUST{100000 + i}"
        is_ring = i in ring_ids
        loc_pool = ELEVATED if (is_ring and rng.random() < 0.35) else COMMON
        country_code, country_name, city, lat, lon, tier = loc_pool[rng.integers(0, len(loc_pool))]

        device_type = DEVICE_TYPES[rng.integers(0, len(DEVICE_TYPES))]
        os = OS_BY_DEVICE[device_type][rng.integers(0, len(OS_BY_DEVICE[device_type]))]
        browser = BROWSERS[rng.integers(0, len(BROWSERS))]
        usual_device_id = (
            ring_device_pool[rng.integers(0, len(ring_device_pool))]
            if is_ring and rng.random() < 0.6
            else make_device_id(rng)
        )

        signup_days_ago = int(rng.integers(30, 1460))
        risk_roll = rng.random()
        risk_segment = "high" if risk_roll < 0.05 else ("medium" if risk_roll < 0.20 else "low")

        rows.append(
            {
                "customer_id": customer_id,
                "full_name": fake.name(),
                "email": fake.email(),
                "phone": fake.phone_number(),
                "home_country_code": country_code,
                "home_country": country_name,
                "home_city": city,
                "home_lat": lat,
                "home_lon": lon,
                "signup_date": (TODAY - timedelta(days=signup_days_ago)).date().isoformat(),
                "risk_segment": risk_segment,
                "is_pep": bool(rng.random() < 0.004),
                "usual_device_id": usual_device_id,
                "usual_device_type": device_type,
                "usual_device_os": os,
                "usual_device_browser": browser,
                "is_known_ring_member": is_ring,  # ground-truth label, NOT exposed to the agent/model
            }
        )
    return pd.DataFrame(rows)


def assign_customers(tx: pd.DataFrame, customers: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    n = len(customers)
    # Heavy-tailed base popularity so most customers transact rarely, a few often.
    base_weights = rng.lognormal(mean=0.0, sigma=1.1, size=n)
    base_weights /= base_weights.sum()

    ring_mask = customers["is_known_ring_member"].to_numpy()
    fraud_weights = np.where(ring_mask, base_weights * 45.0, base_weights)
    fraud_weights /= fraud_weights.sum()

    assigned = np.empty(len(tx), dtype=object)
    fraud_mask = tx["is_fraud"].to_numpy().astype(bool)
    customer_ids = customers["customer_id"].to_numpy()

    assigned[~fraud_mask] = rng.choice(customer_ids, size=(~fraud_mask).sum(), p=base_weights)
    assigned[fraud_mask] = rng.choice(customer_ids, size=fraud_mask.sum(), p=fraud_weights)
    return assigned


def build_transaction_context(
    tx: pd.DataFrame, customers: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    cust_by_id = customers.set_index("customer_id")
    devices_seen = {}  # device_id -> (type, os, browser)

    rows = []
    for row in tx.itertuples(index=False):
        cust = cust_by_id.loc[row.customer_id]
        is_fraud = bool(row.is_fraud)

        p_new_device = 0.55 if is_fraud else 0.06
        p_geo_mismatch = 0.50 if is_fraud else 0.04
        p_vpn = 0.35 if is_fraud else 0.02

        if rng.random() < p_new_device:
            device_id = make_device_id(rng)
            device_type = DEVICE_TYPES[rng.integers(0, len(DEVICE_TYPES))]
            os = OS_BY_DEVICE[device_type][rng.integers(0, len(OS_BY_DEVICE[device_type]))]
            browser = BROWSERS[rng.integers(0, len(BROWSERS))]
            is_new_device = True
        else:
            device_id = cust.usual_device_id
            device_type, os, browser = cust.usual_device_type, cust.usual_device_os, cust.usual_device_browser
            is_new_device = False
        devices_seen.setdefault(device_id, (device_type, os, browser))

        if rng.random() < p_geo_mismatch:
            loc_pool = ELEVATED if (is_fraud and rng.random() < 0.5) else COMMON
            country_code, country_name, city, lat, lon, tier = loc_pool[rng.integers(0, len(loc_pool))]
            lat += rng.normal(0, 0.05)
            lon += rng.normal(0, 0.05)
        else:
            country_code, country_name, city = cust.home_country_code, cust.home_country, cust.home_city
            lat, lon = cust.home_lat + rng.normal(0, 0.02), cust.home_lon + rng.normal(0, 0.02)

        is_vpn = rng.random() < p_vpn
        isp, asn = (HOSTING_ISPS if is_vpn else CONSUMER_ISPS)[
            rng.integers(0, len(HOSTING_ISPS if is_vpn else CONSUMER_ISPS))
        ]

        distance_km = round(haversine_km(cust.home_lat, cust.home_lon, lat, lon), 1)

        rows.append(
            {
                "transaction_id": row.transaction_id,
                "device_id": device_id,
                "device_type": device_type,
                "device_os": os,
                "device_browser": browser,
                "is_new_device_for_customer": is_new_device,
                "ip_address": make_ip(rng),
                "ip_country_code": country_code,
                "ip_country": country_name,
                "ip_city": city,
                "ip_lat": round(float(lat), 4),
                "ip_lon": round(float(lon), 4),
                "isp": isp,
                "asn": asn,
                "is_vpn_or_proxy": bool(is_vpn),
                "distance_from_home_km": distance_km,
            }
        )
    return pd.DataFrame(rows)


def build_merchants(tx: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    counterparties = tx["counterparty_id"].unique()
    fraud_counterparties = set(tx.loc[tx["is_fraud"] == 1, "counterparty_id"].unique())

    rows = []
    for cid in counterparties:
        is_merchant_prefix = cid.startswith("M")
        touched_by_fraud = cid in fraud_counterparties

        if is_merchant_prefix:
            pool = [c for c in MERCHANT_CATEGORIES if c[0] != "peer_transfer"]
        else:
            pool = [c for c in MERCHANT_CATEGORIES if c[0] in ("peer_transfer", "cash_agent")]
        # Fraud-touched counterparties skew toward higher-risk categories.
        if touched_by_fraud and rng.random() < 0.4:
            high_risk_pool = [c for c in pool if c[1]] or pool
            category, is_high_risk = high_risk_pool[rng.integers(0, len(high_risk_pool))]
        else:
            category, is_high_risk = pool[rng.integers(0, len(pool))]

        loc_pool = ELEVATED if (touched_by_fraud and rng.random() < 0.15) else COMMON
        country_code, country_name, city, lat, lon, tier = loc_pool[rng.integers(0, len(loc_pool))]

        watchlist = bool((touched_by_fraud and rng.random() < 0.08) or (not touched_by_fraud and rng.random() < 0.003))

        rows.append(
            {
                "counterparty_id": cid,
                "display_name": fake.company() if is_merchant_prefix else fake.name(),
                "category": category,
                "is_high_risk_category": bool(is_high_risk),
                "country": country_name,
                "country_code": country_code,
                "is_sanctions_watchlist": watchlist,
                "first_seen_date": (TODAY - timedelta(days=int(rng.integers(1, 1460)))).date().isoformat(),
            }
        )
    return pd.DataFrame(rows)


def build_graph_edges(customers: pd.DataFrame, tx_context: pd.DataFrame, tx: pd.DataFrame) -> pd.DataFrame:
    merged = tx_context.merge(tx[["transaction_id", "customer_id"]], on="transaction_id")

    edges = []
    for col, edge_type in [("device_id", "shared_device"), ("ip_address", "shared_ip")]:
        grouped = merged.groupby(col)["customer_id"].unique()
        for value, cust_ids in grouped.items():
            cust_ids = sorted(set(cust_ids))
            if len(cust_ids) < 2:
                continue
            for i in range(len(cust_ids)):
                for j in range(i + 1, len(cust_ids)):
                    edges.append(
                        {
                            "customer_id_a": cust_ids[i],
                            "customer_id_b": cust_ids[j],
                            "edge_type": edge_type,
                            "shared_value": value,
                        }
                    )
    return pd.DataFrame(edges).drop_duplicates()


def main(n_customers: int, n_ring: int, seed: int) -> None:
    rng = np.random.default_rng(seed)

    tx = pd.read_parquet(PROCESSED_DIR / "transactions_base.parquet")
    print(f"Loaded {len(tx):,} transactions")

    print(f"Building {n_customers:,} synthetic customers ({n_ring} ring members)...")
    customers = build_customers(n_customers, n_ring, rng)

    print("Assigning transactions to customers (heavy-tailed, fraud-weighted)...")
    tx = tx.copy()
    tx["customer_id"] = assign_customers(tx, customers, rng)

    print("Synthesizing per-transaction device/IP/geo context...")
    tx_context = build_transaction_context(tx, customers, rng)

    print("Synthesizing counterparty/merchant table...")
    merchants = build_merchants(tx, rng)

    print("Deriving graph edges (shared device / shared IP)...")
    graph_edges = build_graph_edges(customers, tx_context, tx)

    # Ground-truth ring labels stay out of the transactions table the model/agent see;
    # keep them only in customers.parquet for eval-time reference, clearly marked.
    tx.to_parquet(PROCESSED_DIR / "transactions.parquet", index=False)
    customers.to_parquet(PROCESSED_DIR / "customers.parquet", index=False)
    tx_context.to_parquet(PROCESSED_DIR / "transaction_context.parquet", index=False)
    merchants.to_parquet(PROCESSED_DIR / "merchants.parquet", index=False)
    graph_edges.to_parquet(PROCESSED_DIR / "graph_edges.parquet", index=False)

    print(f"customers:           {len(customers):,}")
    print(f"transaction_context: {len(tx_context):,}")
    print(f"merchants:           {len(merchants):,}")
    print(f"graph_edges:         {len(graph_edges):,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-customers", type=int, default=18_000)
    parser.add_argument("--n-ring", type=int, default=250)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    main(args.n_customers, args.n_ring, args.seed)
