import importlib
import os
from contextlib import contextmanager
from typing import Any
from urllib.parse import quote_plus

from dotenv import load_dotenv

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
DB_READ_ONLY = os.getenv("DB_READ_ONLY", "1").strip() in {"1", "true", "True", "yes", "on"}


def _load_postgres_driver() -> Any:
    """Пытается загрузить драйвер PostgreSQL (psycopg2 или psycopg)."""
    for module_name in ("psycopg2", "psycopg"):
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue

    raise RuntimeError(
        "Не найден драйвер PostgreSQL. Установите зависимости: "
        "python3 -m pip install -r requirements.txt"
    )


@contextmanager
def get_connection(dict_cursor: bool = False):
    driver = _load_postgres_driver()

    connect_kwargs = {"connect_timeout": 5}
    if dict_cursor and driver.__name__ == "psycopg2":
        extras = importlib.import_module("psycopg2.extras")
        connect_kwargs["cursor_factory"] = extras.RealDictCursor

    conn = driver.connect(BOT_DB_URL, **connect_kwargs)
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
