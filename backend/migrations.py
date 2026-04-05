"""Lightweight runtime migrations for add-location write path.

Idempotent helpers for environments where write path is enabled.
"""

from . import add_location_contract as contract
from .database import get_db_contract
from .database import get_connection


def ensure_add_location_schema() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                ALTER TABLE IF EXISTS photos
                ADD COLUMN IF NOT EXISTS storage_type TEXT DEFAULT 'telegram',
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
                  telegram_id BIGINT NOT NULL,
                  location_id BIGINT,
                  created_at TIMESTAMPTZ DEFAULT NOW(),
                  UNIQUE (idempotency_key, telegram_id)
                )
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
                ADD COLUMN IF NOT EXISTS theme TEXT DEFAULT 'light'
                """
            )
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower_unique
                ON users (LOWER(email))
                WHERE email IS NOT NULL
                """
            )
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_users_telegram_id_unique
                ON users (telegram_id)
                WHERE telegram_id IS NOT NULL
                """
            )
            cur.execute(
                """
                DO $$
                BEGIN
                  IF NOT EXISTS (
                    SELECT 1 FROM information_schema.views
                    WHERE table_schema='public' AND table_name=%s
                  ) THEN
                    EXECUTE format(
                      'CREATE VIEW %I AS
                        SELECT u.id AS user_id,
                               u.username,
                               u.telegram_id,
                               u.email,
                               u.password_hash AS hashed_password
                        FROM users u',
                      %s
                    );
                  END IF;
                END $$;
                """,
                (contract_views.auth_users_view, contract_views.auth_users_view),
            )
        conn.commit()
