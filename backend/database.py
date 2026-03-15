import os
from contextlib import contextmanager
from urllib.parse import quote_plus

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv()


def _build_postgres_dsn() -> str:
    explicit_url = (os.getenv("DATABASE_URL") or os.getenv("DB_URL") or "").strip()
    if explicit_url:
        return explicit_url

    host = os.getenv("POSTGRES_HOST", "localhost").strip()
    port = os.getenv("POSTGRES_PORT", "5432").strip()
    database = os.getenv("POSTGRES_DB", "friendlymap").strip()
    user = quote_plus(os.getenv("POSTGRES_USER", "postgres").strip())
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", "").strip())

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


BOT_DB_URL = _build_postgres_dsn()


@contextmanager
def get_connection(dict_cursor: bool = False):
    cursor_factory = RealDictCursor if dict_cursor else None
    conn = psycopg2.connect(BOT_DB_URL, connect_timeout=5, cursor_factory=cursor_factory)
    try:
        yield conn
    finally:
        conn.close()


def execute(query: str, params: tuple | None = None) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()


def fetchone(query: str, params: tuple | None = None, dict_cursor: bool = False):
    with get_connection(dict_cursor=dict_cursor) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()


def fetchall(query: str, params: tuple | None = None, dict_cursor: bool = False):
    with get_connection(dict_cursor=dict_cursor) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
