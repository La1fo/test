import hashlib
import hmac
import os
import re
import time

from fastapi import APIRouter, Body, HTTPException

from ..database import DB_READ_ONLY, get_connection, get_db_contract
from ..schemas import UserCreate
from ..security import create_access_token, get_password_hash, verify_password

router = APIRouter()



def _normalize_email(email: str) -> str:
    return email.strip().lower()


TELEGRAM_AUTH_MAX_AGE_SECONDS = int(os.getenv("TELEGRAM_AUTH_MAX_AGE_SECONDS", "86400"))
_TELEGRAM_USERNAME_RE = re.compile(r"[^a-zA-Z0-9_]+")


def _telegram_bot_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Telegram login is not configured")
    return token


def _verify_telegram_auth(auth_data: dict) -> dict[str, str]:
    received_hash = str(auth_data.get("hash") or "")
    if not received_hash:
        raise HTTPException(status_code=400, detail="Telegram auth hash is required")

    try:
        auth_date = int(auth_data.get("auth_date") or 0)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid Telegram auth date") from exc

    if auth_date <= 0 or int(time.time()) - auth_date > TELEGRAM_AUTH_MAX_AGE_SECONDS:
        raise HTTPException(status_code=400, detail="Telegram auth data is expired")

    signed_items = {
        str(key): str(value)
        for key, value in auth_data.items()
        if key not in {"hash", "next"} and value is not None
    }
    if "id" not in signed_items:
        raise HTTPException(status_code=400, detail="Telegram user id is required")

    data_check_string = "\n".join(f"{key}={signed_items[key]}" for key in sorted(signed_items))
    secret_key = hashlib.sha256(_telegram_bot_token().encode()).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise HTTPException(status_code=400, detail="Invalid Telegram auth signature")

    return signed_items


def _telegram_username(auth_data: dict[str, str]) -> str:
    telegram_id = str(auth_data["id"])
    username = (auth_data.get("username") or "").strip().lstrip("@")
    if not username:
        name_parts = [auth_data.get("first_name", ""), auth_data.get("last_name", "")]
        username = "_".join(part.strip() for part in name_parts if part and part.strip())
    username = _TELEGRAM_USERNAME_RE.sub("_", username).strip("_")
    if len(username) < 3:
        username = f"tg_{telegram_id}"
    return username[:64]


def _unique_username(cur, base_username: str, telegram_id: int) -> str:
    candidate = base_username
    cur.execute(
        "SELECT id FROM users WHERE LOWER(username) = LOWER(%s) AND COALESCE(telegram_id, 0) <> %s LIMIT 1",
        (candidate, telegram_id),
    )
    if cur.fetchone() is None:
        return candidate

    candidate = f"{base_username[:48]}_{telegram_id}"
    cur.execute(
        "SELECT id FROM users WHERE LOWER(username) = LOWER(%s) AND COALESCE(telegram_id, 0) <> %s LIMIT 1",
        (candidate, telegram_id),
    )
    if cur.fetchone() is None:
        return candidate
    return f"tg_{telegram_id}"


def _users_columns(cur) -> set[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users'
        """,
    )
    return {row[0] for row in cur.fetchall()}



def _find_user_by_email(cur, email: str):
    users_view = get_db_contract().auth_users_view
    normalized = _normalize_email(email)
    cur.execute(
        f"""
        SELECT user_id, hashed_password
        FROM {users_view}
        WHERE LOWER(email) = %s
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
                cur.execute("SELECT id FROM users WHERE LOWER(email) = %s LIMIT 1", (normalized_email,))
                if cur.fetchone():
                    raise HTTPException(status_code=409, detail="Email already exists")
                cols = _users_columns(cur)
                required_defaults = {
                    "email": normalized_email,
                    "password_hash": get_password_hash(password),
                    "email_verified": False,
                    "total_gp": 0,
                    "pts": 0,
                    "points": 0,
                    "approved_locations": 0,
                    "rejected_locations": 0,
                    "moderation_locations": 0,
                    "achievements_count": 0,
                    "show_name_on_map": True,
                    "notify_points": True,
                    "language": "ru",
                    "theme": "light",
                }
                fields = ["username"]
                values: list[object] = [username.strip()]
                for key, value in required_defaults.items():
                    if key in cols:
                        fields.append(key)
                        values.append(value)
                placeholders = ", ".join(["%s"] * len(values))
                cur.execute(
                    f"INSERT INTO users ({', '.join(fields)}) VALUES ({placeholders}) RETURNING id",
                    tuple(values),
                )
                user_id = int(cur.fetchone()[0])
            conn.commit()
            return user_id
        except Exception:
            conn.rollback()
            raise



def login_telegram_account(auth_data: dict) -> int:
    if DB_READ_ONLY:
        raise HTTPException(status_code=503, detail="Telegram login disabled in read-only DB mode")

    verified = _verify_telegram_auth(auth_data)
    telegram_id = int(verified["id"])
    username = _telegram_username(verified)

    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cols = _users_columns(cur)
                if "telegram_id" not in cols:
                    raise HTTPException(status_code=500, detail="users.telegram_id column is missing")

                cur.execute("SELECT id FROM users WHERE telegram_id = %s LIMIT 1", (telegram_id,))
                row = cur.fetchone()
                if row:
                    user_id = int(row[0])
                    conn.commit()
                    return user_id

                username = _unique_username(cur, username, telegram_id)
                defaults = {
                    "telegram_id": telegram_id,
                    "total_gp": 0,
                    "pts": 0,
                    "points": 0,
                    "approved_locations": 0,
                    "rejected_locations": 0,
                    "moderation_locations": 0,
                    "achievements_count": 0,
                    "show_name_on_map": True,
                    "notify_points": True,
                    "language": "ru",
                    "theme": "light",
                }
                fields = ["username"]
                values: list[object] = [username]
                for key, value in defaults.items():
                    if key in cols:
                        fields.append(key)
                        values.append(value)
                placeholders = ", ".join(["%s"] * len(values))
                cur.execute(
                    f"INSERT INTO users ({', '.join(fields)}) VALUES ({placeholders}) RETURNING id",
                    tuple(values),
                )
                user_id = int(cur.fetchone()[0])
            conn.commit()
            return user_id
        except Exception:
            conn.rollback()
            raise



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


@router.post("/telegram/login")
def login_telegram(auth_data: dict = Body(...)):
    user_id = login_telegram_account(auth_data)
    access_token = create_access_token(data={"sub": str(user_id)})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user_id}
