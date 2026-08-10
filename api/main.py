"""
FastAPI app entrypoint.

Run locally:
    uvicorn api.main:app --reload --port 8000
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from api.db import engine
from api.routes import enrichment, investigations, transactions

app = FastAPI(
    title="Agentic Fraud Investigation System API",
    description="Fraud model scoring, enrichment data, investigation review queue, and audit log.",
    version="0.1.0",
)

# The reviewer dashboard (web/) runs on a different origin (port 5173 in dev) than
# the API (port 8000), so the browser needs an explicit CORS allow — otherwise every
# fetch from the dashboard fails with "Failed to fetch" despite the API working fine
# from curl/Docker-internal calls. WEB_ORIGINS lets this be widened for a deployed
# frontend without code changes.
default_origins = "http://localhost:5173,http://127.0.0.1:5173"
web_origins = os.environ.get("WEB_ORIGINS", default_origins).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=web_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(enrichment.router)
app.include_router(transactions.router)
app.include_router(investigations.router)


@app.on_event("startup")
def on_startup():
    # Creates the app-owned tables (investigation, auditlogentry) if missing.
    # The data tables (customers, transactions, ...) are loaded separately by
    # data/generators/load_to_db.py and are not touched here.
    SQLModel.metadata.create_all(engine)


@app.get("/health")
def health():
    return {"status": "ok"}
