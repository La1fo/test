"""Lightweight runtime migrations for add-location write path.

Idempotent helpers for environments where write path is enabled.
"""

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
        conn.commit()
