"""Shared DB engine for the FastAPI app. SQLite locally (dev.db, produced by
data/generators/load_to_db.py); point DATABASE_URL at Postgres for the
Docker Compose deployment — schema is identical either way.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_URL = f"sqlite:///{ROOT / 'dev.db'}"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DB_URL)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
