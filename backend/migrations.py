"""Lightweight runtime migrations for add-location write path.

Idempotent helpers for environments where write path is enabled.
"""

import re

from . import add_location_contract as contract
from .database import get_db_contract
from .database import get_connection


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _split_relation_name(relation_name: str) -> tuple[str, str]:
    parts = [part.strip() for part in relation_name.split(".") if part.strip()]
    if len(parts) == 1:
        schema, table = "public", parts[0]
    elif len(parts) == 2:
        schema, table = parts
    else:
        raise ValueError(f"Invalid relation name: {relation_name!r}")

    for part in (schema, table):
        if not _IDENTIFIER_RE.fullmatch(part):
            raise ValueError(f"Invalid SQL identifier: {part!r}")
    return schema, table


def _quote_identifier(identifier: str) -> str:
    if not _IDENTIFIER_RE.fullmatch(identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier!r}")
    return f'"{identifier}"'


def _quote_relation(schema: str, table: str) -> str:
    return f"{_quote_identifier(schema)}.{_quote_identifier(table)}"


def ensure_add_location_schema() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                ALTER TABLE IF EXISTS photos
                ADD COLUMN IF NOT EXISTS storage_type TEXT DEFAULT 'legacy',
                ADD COLUMN IF NOT EXISTS storage_path TEXT,
                ADD COLUMN IF NOT EXISTS mime_type TEXT,
                ADD COLUMN IF NOT EXISTS original_name TEXT,
                ADD COLUMN IF NOT EXISTS size_bytes BIGINT
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS site_submission_idempotency (
                  id BIGSERIAL PRIMARY KEY,
                  idempotency_key TEXT NOT NULL,
                  user_id BIGINT NOT NULL,
                  location_id BIGINT,
                  created_at TIMESTAMPTZ DEFAULT NOW(),
                  UNIQUE (idempotency_key, user_id)
                )
                """
            )
            cur.execute("ALTER TABLE site_submission_idempotency ADD COLUMN IF NOT EXISTS user_id BIGINT")
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_site_submission_idempotency_key_user
                ON site_submission_idempotency (idempotency_key, user_id)
                WHERE user_id IS NOT NULL
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tags (
                  id BIGSERIAL PRIMARY KEY,
                  slug TEXT UNIQUE NOT NULL,
                  code TEXT UNIQUE,
                  name TEXT NOT NULL,
                  category TEXT
                )
                """
            )
            for item in contract.TAG_CATALOG:
                cur.execute(
                    """
                    INSERT INTO tags (slug, code, name, category)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (slug) DO UPDATE
                    SET code = EXCLUDED.code, name = EXCLUDED.name, category = EXCLUDED.category
                    """,
                    (item["id"], item["id"], item["label"], item["category"]),
                )
        conn.commit()


def ensure_auth_schema() -> None:
    contract_views = get_db_contract()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                ALTER TABLE IF EXISTS users
                ADD COLUMN IF NOT EXISTS email TEXT,
                ADD COLUMN IF NOT EXISTS password_hash TEXT,
                ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS approved_locations INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS rejected_locations INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS moderation_locations INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS achievements_count INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS show_name_on_map BOOLEAN DEFAULT TRUE,
                ADD COLUMN IF NOT EXISTS notify_points BOOLEAN DEFAULT TRUE,
                ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'ru',
                ADD COLUMN IF NOT EXISTS theme TEXT DEFAULT 'light',
                ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE
                """
            )
            cur.execute(
                """
                UPDATE users
                SET is_admin = TRUE
                WHERE LOWER(username) = 'laifo'
                """
            )
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower_unique
                ON users (LOWER(email))
                WHERE email IS NOT NULL
                """
            )
            view_schema, view_name = _split_relation_name(contract_views.auth_users_view)
            cur.execute(
                """
                SELECT 1
                FROM information_schema.views
                WHERE table_schema = %s AND table_name = %s
                LIMIT 1
                """,
                (view_schema, view_name),
            )
            if cur.fetchone() is None:
                cur.execute(
                    f"""
                    CREATE VIEW {_quote_relation(view_schema, view_name)} AS
                    SELECT u.id AS user_id,
                           u.username,
                           u.telegram_id,
                           u.email,
                           u.password_hash AS hashed_password
                    FROM users u
                    """
                )
        conn.commit()
