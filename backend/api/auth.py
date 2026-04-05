import os

from fastapi import APIRouter, Body, HTTPException

from ..database import DB_READ_ONLY, get_connection, get_db_contract
from ..schemas import TelegramAuthPayload, UserCreate
from ..security import create_access_token, get_password_hash, verify_password, verify_telegram_auth

router = APIRouter()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


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
                    "telegram_id": None,
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
                    cols = _users_columns(cur)
                    fields = ["username"]
                    values: list[object] = [display_username]
                    if "telegram_id" in cols:
                        fields.append("telegram_id")
                        values.append(telegram_id)
                    if "email_verified" in cols:
                        fields.append("email_verified")
                        values.append(False)
                    if "total_gp" in cols:
                        fields.append("total_gp")
                        values.append(0)
                    if "moderation_locations" in cols:
                        fields.append("moderation_locations")
                        values.append(0)
                    if "show_name_on_map" in cols:
                        fields.append("show_name_on_map")
                        values.append(True)
                    if "notify_points" in cols:
                        fields.append("notify_points")
                        values.append(True)
                    if "language" in cols:
                        fields.append("language")
                        values.append("ru")
                    if "theme" in cols:
                        fields.append("theme")
                        values.append("light")
                    placeholders = ", ".join(["%s"] * len(values))
                    cur.execute(
                        f"INSERT INTO users ({', '.join(fields)}) VALUES ({placeholders}) RETURNING id",
                        tuple(values),
                    )
                    user_id = int(cur.fetchone()[0])
                if not DB_READ_ONLY:
                    cur.execute(
                        """
                        UPDATE users
                        SET username = COALESCE(NULLIF(%s, ''), username),
                            first_name = COALESCE(%s, first_name),
                            last_name = COALESCE(%s, last_name)
                        WHERE id = %s
                        """,
                        (display_username, first_name, last_name, user_id),
                    )
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
