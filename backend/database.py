import importlib
import os
import re
from contextlib import contextmanager
from functools import lru_cache
from typing import Any
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()

_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


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

TABLE_CANDIDATES = {
    "users": [
        os.getenv("FM_USERS_TABLE", "").strip(),
        "website_users",
        "users",
        "fm_users",
    ],
    "achievements": [
        os.getenv("FM_ACHIEVEMENTS_TABLE", "").strip(),
        "website_achievements",
        "achievements",
        "fm_achievements",
    ],
    "user_achievements": [
        os.getenv("FM_USER_ACHIEVEMENTS_TABLE", "").strip(),
        "website_user_achievements",
        "user_achievements",
        "fm_user_achievements",
    ],
}


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


def _assert_identifier(name: str) -> str:
    if not name or not _IDENTIFIER_RE.match(name):
        raise RuntimeError(f"Некорректное имя таблицы: {name!r}")
    return name


def _table_exists(cur, table_name: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = %s
        LIMIT 1
        """,
        (table_name,),
    )
    return cur.fetchone() is not None


@lru_cache(maxsize=1)
def resolve_table_mapping() -> dict[str, str]:
    """Определяет имена таблиц в уже существующей FriendlyMap DB."""
    mapping: dict[str, str] = {}
    missing: dict[str, list[str]] = {}

    with get_connection() as conn:
        with conn.cursor() as cur:
            for logical_name, candidates in TABLE_CANDIDATES.items():
                normalized = [_assert_identifier(c) for c in candidates if c]
                for candidate in normalized:
                    if _table_exists(cur, candidate):
                        mapping[logical_name] = candidate
                        break
                if logical_name not in mapping:
                    missing[logical_name] = normalized

    if missing:
        details = "; ".join(
            f"{logical}: tried {', '.join(cands)}" for logical, cands in missing.items()
        )
        raise RuntimeError(
            "Не удалось найти нужные таблицы в существующей БД FriendlyMap. "
            f"{details}. Укажите точные имена через FM_*_TABLE в .env"
        )

    return mapping


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
