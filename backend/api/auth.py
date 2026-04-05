import os
import secrets

from fastapi import APIRouter, Body, HTTPException

from ..database import DB_READ_ONLY, get_connection, get_db_contract
from ..schemas import TelegramAuthPayload, UserCreate
from ..security import create_access_token, get_password_hash, verify_password, verify_telegram_auth

router = APIRouter()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
SITE_AUTH_TABLE = os.getenv("SITE_AUTH_TABLE", "site_auth_accounts").strip()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _users_columns(cur) -> set[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users'
        """,
    )
    return {row[0] for row in cur.fetchall()}


def _insert_user(cur, username: str, telegram_id: int | None = None) -> int:
    cols = _users_columns(cur)
    if "username" not in cols:
        raise HTTPException(status_code=500, detail="users.username column is required")

    fields = ["username"]
    values: list[object] = [username]

    if "telegram_id" in cols:
        fields.append("telegram_id")
        values.append(telegram_id)
    if "first_name" in cols:
        fields.append("first_name")
        values.append(username[:64])
    if "last_name" in cols:
        fields.append("last_name")
        values.append(None)
    if "moderation_locations" in cols:
        fields.append("moderation_locations")
        values.append(0)
    if "total_gp" in cols:
        fields.append("total_gp")
        values.append(0)

    placeholders = ", ".join(["%s"] * len(values))
    cur.execute(
        f"INSERT INTO users ({', '.join(fields)}) VALUES ({placeholders}) RETURNING id",
        tuple(values),
    )
    return int(cur.fetchone()[0])


def _upsert_auth_account(
    cur,
    *,
    user_id: int,
    email: str | None,
    hashed_password: str | None,
    telegram_id: int | None,
) -> None:
    safe_hash = hashed_password or get_password_hash(secrets.token_urlsafe(32))
    cur.execute(
        f"""
        INSERT INTO {SITE_AUTH_TABLE} (user_id, email, hashed_password, telegram_id)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            email = COALESCE(EXCLUDED.email, {SITE_AUTH_TABLE}.email),
            hashed_password = COALESCE(EXCLUDED.hashed_password, {SITE_AUTH_TABLE}.hashed_password),
            telegram_id = COALESCE(EXCLUDED.telegram_id, {SITE_AUTH_TABLE}.telegram_id),
            updated_at = NOW()
        """,
        (user_id, email, safe_hash, telegram_id),
    )


def _find_user_by_email(cur, email: str):
    users_view = get_db_contract().auth_users_view
    normalized = _normalize_email(email)
    cur.execute(
        f"""
        SELECT user_id, hashed_password
        FROM (
            SELECT user_id, hashed_password, LOWER(email) AS norm_email FROM {users_view}
            UNION ALL
            SELECT user_id, hashed_password, LOWER(email) AS norm_email FROM {SITE_AUTH_TABLE}
        ) src
        WHERE norm_email = %s
        LIMIT 1
        """,
        (normalized,),
    )
    return cur.fetchone()


def register_email_account(*, username: str, email: str, password: str) -> int:
    if DB_READ_ONLY:
        raise HTTPException(status_code=503, detail="Registration disabled in read-only DB mode")
    if len(username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    normalized_email = _normalize_email(email)
    if "@" not in normalized_email or normalized_email.startswith("@") or normalized_email.endswith("@"):
        raise HTTPException(status_code=400, detail="Invalid email format")
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(%s) LIMIT 1", (username.strip(),))
                if cur.fetchone():
                    raise HTTPException(status_code=409, detail="Username already exists")
                cur.execute(f"SELECT user_id FROM {SITE_AUTH_TABLE} WHERE LOWER(email) = %s LIMIT 1", (normalized_email,))
                if cur.fetchone():
                    raise HTTPException(status_code=409, detail="Email already exists")

                user_id = _insert_user(cur, username=username.strip(), telegram_id=None)
                _upsert_auth_account(
                    cur,
                    user_id=user_id,
                    email=normalized_email,
                    hashed_password=get_password_hash(password),
                    telegram_id=None,
                )
            conn.commit()
            return user_id
        except Exception:
            conn.rollback()
            raise


def ensure_telegram_user(*, telegram_id: int, username: str | None, first_name: str | None, last_name: str | None) -> int:
    display_username = (username or first_name or f"user_{telegram_id}").strip()
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE telegram_id = %s LIMIT 1", (telegram_id,))
                row = cur.fetchone()
                if row:
                    user_id = int(row[0])
                    if DB_READ_ONLY:
                        return user_id
                else:
                    if DB_READ_ONLY:
                        raise HTTPException(status_code=503, detail="Telegram bootstrap disabled in read-only DB mode")
                    user_id = _insert_user(cur, username=display_username, telegram_id=telegram_id)
                _upsert_auth_account(cur, user_id=user_id, email=None, hashed_password=None, telegram_id=telegram_id)
            conn.commit()
            return user_id
        except Exception:
            conn.rollback()
            raise


@router.post("/telegram")
def login_telegram(payload: TelegramAuthPayload):
    data = payload.model_dump(exclude_none=True)

    if not verify_telegram_auth(data, TELEGRAM_BOT_TOKEN):
        raise HTTPException(status_code=400, detail="Invalid Telegram auth")

    telegram_id = int(data["id"])
    users_view = get_db_contract().auth_users_view

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT user_id FROM {users_view} WHERE telegram_id = %s",
                (telegram_id,),
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(
            status_code=403,
            detail="User does not exist in shared FriendlyMap DB. Registration is handled by writer services.",
        )

    user_id = row[0]
    access_token = create_access_token(data={"sub": str(user_id)})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user_id}


@router.post("/email/register")
def register_email(user: UserCreate):
    user_id = register_email_account(username=user.username, email=user.email, password=user.password)
    access_token = create_access_token(data={"sub": str(user_id)})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user_id}


@router.post("/email/login")
def login_email(email: str = Body(...), password: str = Body(...)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            row = _find_user_by_email(cur, email)

    if row is None:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    user_id, hashed_password = row
    if not hashed_password or not verify_password(password, hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": str(user_id)})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user_id}
