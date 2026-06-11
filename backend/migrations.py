"""Lightweight runtime migrations for the standalone website.

All helpers are idempotent and are meant for environments where the site has
write access to its own PostgreSQL schema.  Read-only deployments can still use
pre-created tables/views and only run DB contract validation.
"""

from . import add_location_contract as contract
from .database import get_db_contract
from .database import get_connection


def ensure_core_schema() -> None:
    """Create the base tables used by the website if they do not exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                  id BIGSERIAL PRIMARY KEY,
                  telegram_id BIGINT UNIQUE,
                  username TEXT NOT NULL,
                  email TEXT,
                  password_hash TEXT,
                  email_verified BOOLEAN DEFAULT FALSE,
                  total_gp INTEGER NOT NULL DEFAULT 0,
                  pts INTEGER NOT NULL DEFAULT 0,
                  points INTEGER NOT NULL DEFAULT 0,
                  approved_locations INTEGER NOT NULL DEFAULT 0,
                  rejected_locations INTEGER NOT NULL DEFAULT 0,
                  moderation_locations INTEGER NOT NULL DEFAULT 0,
                  achievements_count INTEGER NOT NULL DEFAULT 0,
                  show_name_on_map BOOLEAN NOT NULL DEFAULT TRUE,
                  notify_points BOOLEAN NOT NULL DEFAULT TRUE,
                  language TEXT NOT NULL DEFAULT 'ru',
                  theme TEXT NOT NULL DEFAULT 'light',
                  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                ALTER TABLE IF EXISTS users
                ADD COLUMN IF NOT EXISTS telegram_id BIGINT,
                ADD COLUMN IF NOT EXISTS username TEXT,
                ADD COLUMN IF NOT EXISTS email TEXT,
                ADD COLUMN IF NOT EXISTS password_hash TEXT,
                ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS total_gp INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS pts INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS points INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS approved_locations INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS rejected_locations INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS moderation_locations INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS achievements_count INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS show_name_on_map BOOLEAN DEFAULT TRUE,
                ADD COLUMN IF NOT EXISTS notify_points BOOLEAN DEFAULT TRUE,
                ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'ru',
                ADD COLUMN IF NOT EXISTS theme TEXT DEFAULT 'light',
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()
                """
            )
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_lower_unique ON users (LOWER(username))")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS locations (
                  id BIGSERIAL PRIMARY KEY,
                  user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
                  name TEXT NOT NULL,
                  description TEXT,
                  latitude DOUBLE PRECISION NOT NULL,
                  longitude DOUBLE PRECISION NOT NULL,
                  status TEXT NOT NULL DEFAULT 'pending',
                  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  approved_at TIMESTAMPTZ
                )
                """
            )
            cur.execute(
                """
                ALTER TABLE IF EXISTS locations
                ADD COLUMN IF NOT EXISTS user_id BIGINT,
                ADD COLUMN IF NOT EXISTS name TEXT,
                ADD COLUMN IF NOT EXISTS description TEXT,
                ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION,
                ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION,
                ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending',
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW(),
                ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_locations_status ON locations (status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_locations_user_id ON locations (user_id)")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS photos (
                  id BIGSERIAL PRIMARY KEY,
                  location_id BIGINT NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
                  file_id TEXT,
                  description TEXT,
                  order_index INTEGER NOT NULL DEFAULT 0,
                  storage_type TEXT NOT NULL DEFAULT 'legacy',
                  storage_path TEXT,
                  mime_type TEXT,
                  original_name TEXT,
                  size_bytes BIGINT,
                  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                ALTER TABLE IF EXISTS photos
                ADD COLUMN IF NOT EXISTS location_id BIGINT,
                ADD COLUMN IF NOT EXISTS file_id TEXT,
                ADD COLUMN IF NOT EXISTS description TEXT,
                ADD COLUMN IF NOT EXISTS order_index INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS storage_type TEXT DEFAULT 'legacy',
                ADD COLUMN IF NOT EXISTS storage_path TEXT,
                ADD COLUMN IF NOT EXISTS mime_type TEXT,
                ADD COLUMN IF NOT EXISTS original_name TEXT,
                ADD COLUMN IF NOT EXISTS size_bytes BIGINT,
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_photos_location_id ON photos (location_id)")
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
            cur.execute(
                """
                ALTER TABLE IF EXISTS tags
                ADD COLUMN IF NOT EXISTS slug TEXT,
                ADD COLUMN IF NOT EXISTS code TEXT,
                ADD COLUMN IF NOT EXISTS name TEXT,
                ADD COLUMN IF NOT EXISTS category TEXT
                """
            )
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tags_slug_unique ON tags (slug)")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tags_code_unique ON tags (code) WHERE code IS NOT NULL")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS location_tags (
                  location_id BIGINT NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
                  tag_id BIGINT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                  PRIMARY KEY (location_id, tag_id)
                )
                """
            )
            cur.execute(
                """
                ALTER TABLE IF EXISTS location_tags
                ADD COLUMN IF NOT EXISTS location_id BIGINT,
                ADD COLUMN IF NOT EXISTS tag_id BIGINT
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_location_tags_tag_id ON location_tags (tag_id)")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS achievements (
                  id TEXT PRIMARY KEY,
                  code TEXT UNIQUE NOT NULL,
                  name TEXT NOT NULL,
                  description TEXT,
                  reward_points INTEGER NOT NULL DEFAULT 0,
                  is_seasonal BOOLEAN NOT NULL DEFAULT FALSE,
                  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                ALTER TABLE IF EXISTS achievements
                ADD COLUMN IF NOT EXISTS code TEXT,
                ADD COLUMN IF NOT EXISTS name TEXT,
                ADD COLUMN IF NOT EXISTS description TEXT,
                ADD COLUMN IF NOT EXISTS reward_points INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS is_seasonal BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_achievements (
                  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                  achievement_id TEXT NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
                  unlocked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  PRIMARY KEY (user_id, achievement_id)
                )
                """
            )
            cur.execute(
                """
                ALTER TABLE IF EXISTS user_achievements
                ADD COLUMN IF NOT EXISTS user_id BIGINT,
                ADD COLUMN IF NOT EXISTS achievement_id TEXT,
                ADD COLUMN IF NOT EXISTS unlocked_at TIMESTAMPTZ DEFAULT NOW()
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_user_achievements_achievement_id ON user_achievements (achievement_id)")
        conn.commit()


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
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tags_slug_unique ON tags (slug)")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tags_code_unique ON tags (code) WHERE code IS NOT NULL")
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
        conn.commit()


def ensure_contract_views() -> None:
    """Create or replace all contract views consumed by the website."""
    contract_views = get_db_contract()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                CREATE OR REPLACE VIEW {contract_views.public_users_view} AS
                WITH location_counts AS (
                  SELECT user_id, COUNT(*)::INTEGER AS approved_count
                  FROM locations
                  WHERE status = 'approved'
                  GROUP BY user_id
                ), ranked_users AS (
                  SELECT
                    u.id AS user_id,
                    u.username,
                    u.telegram_id,
                    GREATEST(COALESCE(u.total_gp, 0), COALESCE(u.pts, 0), COALESCE(u.points, 0))::INTEGER AS total_gp,
                    GREATEST(COALESCE(u.approved_locations, 0), COALESCE(lc.approved_count, 0))::INTEGER AS approved_locations
                  FROM users u
                  LEFT JOIN location_counts lc ON lc.user_id = u.id
                )
                SELECT
                  user_id,
                  username,
                  telegram_id,
                  total_gp,
                  (FLOOR(total_gp / 100.0)::INTEGER + 1) AS rank_level,
                  (total_gp % 100)::INTEGER AS gp_in_rank,
                  ('Ранг ' || (FLOOR(total_gp / 100.0)::INTEGER + 1)) AS rank_name,
                  approved_locations
                FROM ranked_users
                """
            )
            cur.execute(
                f"""
                CREATE OR REPLACE VIEW {contract_views.leaderboard_view} AS
                SELECT
                  user_id,
                  username,
                  total_gp,
                  rank_level,
                  gp_in_rank,
                  rank_name,
                  ROW_NUMBER() OVER (ORDER BY total_gp DESC, user_id ASC)::INTEGER AS position
                FROM {contract_views.public_users_view}
                """
            )
            cur.execute(
                f"""
                CREATE OR REPLACE VIEW {contract_views.public_locations_view} AS
                SELECT id AS location_id, user_id
                FROM locations
                WHERE status = 'approved'
                """
            )
            cur.execute(
                f"""
                CREATE OR REPLACE VIEW {contract_views.achievements_view} AS
                SELECT
                  a.id AS achievement_id,
                  a.code,
                  a.name,
                  a.description,
                  COUNT(ua.user_id)::INTEGER AS completed_count,
                  a.is_seasonal
                FROM achievements a
                LEFT JOIN user_achievements ua ON ua.achievement_id = a.id
                GROUP BY a.id, a.code, a.name, a.description, a.is_seasonal
                """
            )
            cur.execute(
                f"""
                CREATE OR REPLACE VIEW {contract_views.auth_users_view} AS
                SELECT
                  u.id AS user_id,
                  u.username,
                  u.telegram_id,
                  u.email,
                  u.password_hash AS hashed_password
                FROM users u
                """
            )
        conn.commit()


def ensure_site_schema() -> None:
    """Create all tables, seed catalogs, and expose DB contract views."""
    ensure_core_schema()
    ensure_add_location_schema()
    ensure_auth_schema()
    ensure_contract_views()
