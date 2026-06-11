import importlib
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()

_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


@dataclass(frozen=True)
class DBContract:
    leaderboard_view: str
    public_users_view: str
    public_locations_view: str
    achievements_view: str
    auth_users_view: str


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _assert_identifier(name: str) -> str:
    if not name or not _IDENTIFIER_RE.match(name):
        raise RuntimeError(f"Некорректное SQL-имя объекта: {name!r}")
    return name


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


DATABASE_DSN = _build_postgres_dsn()
DB_READ_ONLY = _bool_env("DB_READ_ONLY", False)
DB_BOOTSTRAP_SCHEMA = _bool_env("DB_BOOTSTRAP_SCHEMA", True)
LEGACY_SCHEMA_COMPAT = _bool_env("LEGACY_SCHEMA_COMPAT", False)


def get_db_contract() -> DBContract:
    return DBContract(
        leaderboard_view=_assert_identifier(
            os.getenv("SITE_LEADERBOARD_VIEW", "site_leaderboard").strip()
        ),
        public_users_view=_assert_identifier(
            os.getenv("SITE_PUBLIC_USERS_VIEW", "site_public_users").strip()
        ),
        public_locations_view=_assert_identifier(
            os.getenv("SITE_PUBLIC_LOCATIONS_VIEW", "site_public_locations").strip()
        ),
        achievements_view=_assert_identifier(
            os.getenv("SITE_ACHIEVEMENTS_VIEW", "site_achievements_overview").strip()
        ),
        auth_users_view=_assert_identifier(
            os.getenv("SITE_AUTH_USERS_VIEW", "site_auth_users").strip()
        ),
    )


def _load_postgres_driver() -> Any:
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

    conn = driver.connect(DATABASE_DSN, **connect_kwargs)
    try:
        yield conn
    finally:
        conn.close()


def _view_columns(cur, view_name: str) -> set[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        """,
        (view_name,),
    )
    return {row[0] for row in cur.fetchall()}


def _view_exists(cur, view_name: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.views
        WHERE table_schema='public' AND table_name=%s
        LIMIT 1
        """,
        (view_name,),
    )
    return cur.fetchone() is not None


REQUIRED_COLUMNS = {
    "leaderboard": {"user_id", "username", "total_gp", "rank_level", "gp_in_rank", "rank_name", "position"},
    "public_users": {"user_id", "username", "telegram_id", "total_gp", "rank_level", "gp_in_rank", "rank_name", "approved_locations"},
    "public_locations": {"location_id", "user_id"},
    "achievements": {"achievement_id", "code", "name", "description", "completed_count", "is_seasonal"},
    "auth_users": {"user_id", "username", "telegram_id", "email", "hashed_password"},
}


def validate_db_contract() -> tuple[bool, list[str]]:
    contract = get_db_contract()
    errors: list[str] = []

    with get_connection() as conn:
        with conn.cursor() as cur:
            for key, view_name in (
                ("leaderboard", contract.leaderboard_view),
                ("public_users", contract.public_users_view),
                ("public_locations", contract.public_locations_view),
                ("achievements", contract.achievements_view),
                ("auth_users", contract.auth_users_view),
            ):
                if not _view_exists(cur, view_name):
                    errors.append(f"view '{view_name}' отсутствует")
                    continue

                cols = _view_columns(cur, view_name)
                missing = REQUIRED_COLUMNS[key] - cols
                if missing:
                    errors.append(
                        f"view '{view_name}' не содержит колонки: {', '.join(sorted(missing))}"
                    )

    return len(errors) == 0, errors


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


LEGACY_TABLE_CANDIDATES = {
    "users": ["website_users", "users", "fm_users"],
    "achievements": ["website_achievements", "achievements", "fm_achievements"],
    "user_achievements": ["website_user_achievements", "user_achievements", "fm_user_achievements"],
}


def _table_exists(cur, table_name: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema='public' AND table_name=%s
        LIMIT 1
        """,
        (table_name,),
    )
    return cur.fetchone() is not None


@lru_cache(maxsize=1)
def resolve_table_mapping() -> dict[str, str]:
    if not LEGACY_SCHEMA_COMPAT:
        raise RuntimeError(
            "Legacy schema mapping отключён. Используйте контрактные VIEW (site_*). "
            "Для временной совместимости установите LEGACY_SCHEMA_COMPAT=1"
        )

    mapping: dict[str, str] = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            for logical_name, candidates in LEGACY_TABLE_CANDIDATES.items():
                for candidate in candidates:
                    if _table_exists(cur, candidate):
                        mapping[logical_name] = candidate
                        break
                if logical_name not in mapping:
                    raise RuntimeError(f"Legacy таблица для '{logical_name}' не найдена")

    return mapping


@lru_cache(maxsize=16)
def get_table_columns(table_name: str) -> set[str]:
    table_name = _assert_identifier(table_name)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                """,
                (table_name,),
            )
            return {row[0] for row in cur.fetchall()}


def resolve_column(table_name: str, candidates: list[str]) -> str | None:
    if not LEGACY_SCHEMA_COMPAT:
        raise RuntimeError(
            "Legacy column resolve отключён. Используйте фиксированные колонки контрактных VIEW."
        )
    columns = get_table_columns(table_name)
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None
