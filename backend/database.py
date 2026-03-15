import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DEFAULT_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/friendly_map"
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL") or DEFAULT_DATABASE_URL


def _validate_database_url(db_url: str) -> str:
    allowed_prefixes = ("postgresql://", "postgresql+psycopg2://")
    if not db_url.startswith(allowed_prefixes):
        raise ValueError("DATABASE_URL must point to PostgreSQL (postgresql:// or postgresql+psycopg2://)")
    return db_url


engine = create_engine(
    _validate_database_url(DATABASE_URL),
    pool_pre_ping=True,
    pool_recycle=1800,
    future=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
