"""
Internal enrichment endpoints — the data-serving half of the API that the
Investigation Agent's tools (agent/tools/) call over HTTP. Each endpoint's
shape is deliberately kept close to what a real MCP server (IPinfo,
AbuseIPDB, a graph DB) would return, so a real one can be swapped in later
without changing the agent's tool interface.

All "history"/"reputation" aggregates are computed causally — using only
transactions with an earlier `step` than the one under investigation — so
the agent never sees information that wouldn't have existed yet in a real
investigation.
"""
import math
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from data.generators.geo_reference import TODAY  # noqa: E402
from api.db import get_db  # noqa: E402

router = APIRouter(prefix="/internal/enrichment", tags=["enrichment"])

IMPOSSIBLE_TRAVEL_SPEED_KMH = 900  # ~ commercial flight cruising speed


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _get_transaction(db: Session, transaction_id: str) -> Dict[str, Any]:
    row = db.execute(
        text("SELECT * FROM transactions WHERE transaction_id = :tid"), {"tid": transaction_id}
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"transaction {transaction_id} not found")
    return dict(row)


@router.get("/geo-ip/{transaction_id}")
def geo_ip_lookup(transaction_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """IP/device/geo evidence for one transaction, plus an impossible-travel
    check against the customer's immediately preceding transaction.
    """
    tx = _get_transaction(db, transaction_id)

    ctx = db.execute(
        text(
            """
            SELECT tc.*, c.home_country, c.home_city, c.home_lat, c.home_lon
            FROM transaction_context tc
            JOIN customers c ON c.customer_id = :customer_id
            WHERE tc.transaction_id = :tid
            """
        ),
        {"tid": transaction_id, "customer_id": tx["customer_id"]},
    ).mappings().first()
    if ctx is None:
        raise HTTPException(status_code=404, detail="no context for this transaction")
    ctx = dict(ctx)

    country_mismatch = ctx["ip_country"] != ctx["home_country"]

    prev = db.execute(
        text(
            """
            SELECT t.transaction_id, t.step, tc.ip_lat, tc.ip_lon, tc.ip_country, tc.ip_city
            FROM transactions t
            JOIN transaction_context tc ON tc.transaction_id = t.transaction_id
            WHERE t.customer_id = :customer_id AND t.step < :step
            ORDER BY t.step DESC LIMIT 1
            """
        ),
        {"customer_id": tx["customer_id"], "step": tx["step"]},
    ).mappings().first()

    impossible_travel = None
    if prev is not None:
        hours_elapsed = tx["step"] - prev["step"]
        distance_km = haversine_km(prev["ip_lat"], prev["ip_lon"], ctx["ip_lat"], ctx["ip_lon"])
        speed_kmh = distance_km / hours_elapsed if hours_elapsed > 0 else None
        impossible_travel = {
            "previous_transaction_id": prev["transaction_id"],
            "previous_location": f"{prev['ip_city']}, {prev['ip_country']}",
            "hours_since_previous_transaction": hours_elapsed,
            "distance_km": round(distance_km, 1),
            "implied_speed_kmh": round(speed_kmh, 1) if speed_kmh is not None else None,
            "is_physically_implausible": bool(speed_kmh and speed_kmh > IMPOSSIBLE_TRAVEL_SPEED_KMH),
        }

    return {
        "transaction_id": transaction_id,
        "ip_address": ctx["ip_address"],
        "ip_location": {"country": ctx["ip_country"], "city": ctx["ip_city"]},
        "isp": ctx["isp"],
        "asn": ctx["asn"],
        "is_vpn_or_proxy": bool(ctx["is_vpn_or_proxy"]),
        "device": {
            "device_id": ctx["device_id"],
            "type": ctx["device_type"],
            "os": ctx["device_os"],
            "browser": ctx["device_browser"],
            "is_new_device_for_customer": bool(ctx["is_new_device_for_customer"]),
        },
        "customer_home_location": {"country": ctx["home_country"], "city": ctx["home_city"]},
        "country_mismatch_vs_home": bool(country_mismatch),
        "distance_from_home_km": ctx["distance_from_home_km"],
        "impossible_travel_check": impossible_travel,
    }


@router.get("/customer-history/{transaction_id}")
def customer_history(transaction_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Customer profile + behavioral history, using only transactions that
    happened before the one under investigation.
    """
    tx = _get_transaction(db, transaction_id)
    customer_id, current_step = tx["customer_id"], tx["step"]

    profile = db.execute(
        text("SELECT * FROM customers WHERE customer_id = :cid"), {"cid": customer_id}
    ).mappings().first()
    if profile is None:
        raise HTTPException(status_code=404, detail="customer not found")
    profile = dict(profile)

    prior = db.execute(
        text(
            """
            SELECT transaction_id, step, type, amount, is_fraud
            FROM transactions
            WHERE customer_id = :cid AND step < :step
            ORDER BY step DESC
            """
        ),
        {"cid": customer_id, "step": current_step},
    ).mappings().all()
    prior = [dict(r) for r in prior]

    account_age_days = (TODAY.date() - date.fromisoformat(profile["signup_date"])).days
    amounts = [r["amount"] for r in prior]
    recent_window = [r for r in prior if current_step - r["step"] <= 24 * 7]

    return {
        "transaction_id": transaction_id,
        "customer_id": customer_id,
        "profile": {
            "full_name": profile["full_name"],
            "home_country": profile["home_country"],
            "home_city": profile["home_city"],
            "signup_date": profile["signup_date"],
            "account_age_days": account_age_days,
            "risk_segment": profile["risk_segment"],
            "is_politically_exposed_person": bool(profile["is_pep"]),
        },
        "history_summary": {
            "prior_transaction_count": len(prior),
            "avg_prior_amount": round(sum(amounts) / len(amounts), 2) if amounts else None,
            "max_prior_amount": round(max(amounts), 2) if amounts else None,
            "confirmed_fraud_count": sum(r["is_fraud"] for r in prior),
            "transactions_last_7d": len(recent_window),
            "is_first_transaction": len(prior) == 0,
        },
        "recent_transactions": [
            {
                "transaction_id": r["transaction_id"],
                "step": r["step"],
                "type": r["type"],
                "amount": r["amount"],
                "confirmed_fraud": bool(r["is_fraud"]),
            }
            for r in prior[:5]
        ],
    }


@router.get("/graph/{transaction_id}")
def graph_features(transaction_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Accounts linked to this transaction's customer via shared device or IP,
    and each linked account's own confirmed-fraud track record.
    """
    tx = _get_transaction(db, transaction_id)
    customer_id = tx["customer_id"]

    edges = db.execute(
        text(
            """
            SELECT customer_id_a, customer_id_b, edge_type, shared_value
            FROM graph_edges
            WHERE customer_id_a = :cid OR customer_id_b = :cid
            """
        ),
        {"cid": customer_id},
    ).mappings().all()

    linked: List[Dict[str, Any]] = []
    for e in edges:
        other_id = e["customer_id_b"] if e["customer_id_a"] == customer_id else e["customer_id_a"]
        stats = db.execute(
            text(
                """
                SELECT COUNT(*) AS txn_count, COALESCE(SUM(is_fraud), 0) AS fraud_count
                FROM transactions WHERE customer_id = :cid
                """
            ),
            {"cid": other_id},
        ).mappings().first()
        txn_count, fraud_count = stats["txn_count"], stats["fraud_count"]
        linked.append(
            {
                "linked_customer_id": other_id,
                "edge_type": e["edge_type"],
                "shared_value": e["shared_value"],
                "linked_customer_txn_count": txn_count,
                "linked_customer_confirmed_fraud_count": fraud_count,
                "linked_customer_fraud_rate": round(fraud_count / txn_count, 3) if txn_count else None,
            }
        )

    fraud_rates = [l["linked_customer_fraud_rate"] for l in linked if l["linked_customer_fraud_rate"] is not None]
    return {
        "transaction_id": transaction_id,
        "customer_id": customer_id,
        "network_degree": len(linked),
        "linked_accounts": linked,
        "max_linked_account_fraud_rate": max(fraud_rates) if fraud_rates else None,
    }


@router.get("/reputation/{transaction_id}")
def reputation_check(transaction_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Counterparty (merchant/peer) reputation: category risk, sanctions
    watchlist flag, and its own historical fraud-involvement rate, computed
    only from transactions that happened before this one.
    """
    tx = _get_transaction(db, transaction_id)
    counterparty_id, current_step = tx["counterparty_id"], tx["step"]

    merchant = db.execute(
        text("SELECT * FROM merchants WHERE counterparty_id = :cid"), {"cid": counterparty_id}
    ).mappings().first()
    if merchant is None:
        raise HTTPException(status_code=404, detail="counterparty not found")
    merchant = dict(merchant)

    stats = db.execute(
        text(
            """
            SELECT COUNT(*) AS txn_count, COALESCE(SUM(is_fraud), 0) AS fraud_count
            FROM transactions
            WHERE counterparty_id = :cid AND step < :step
            """
        ),
        {"cid": counterparty_id, "step": current_step},
    ).mappings().first()
    txn_count, fraud_count = stats["txn_count"], stats["fraud_count"]

    return {
        "transaction_id": transaction_id,
        "counterparty_id": counterparty_id,
        "display_name": merchant["display_name"],
        "category": merchant["category"],
        "is_high_risk_category": bool(merchant["is_high_risk_category"]),
        "country": merchant["country"],
        "is_sanctions_watchlist": bool(merchant["is_sanctions_watchlist"]),
        "first_seen_date": merchant["first_seen_date"],
        "prior_transaction_count": txn_count,
        "prior_confirmed_fraud_count": fraud_count,
        "prior_fraud_rate": round(fraud_count / txn_count, 3) if txn_count else None,
    }
