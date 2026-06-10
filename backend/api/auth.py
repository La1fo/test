from fastapi import APIRouter, Body, HTTPException

from ..database import DB_READ_ONLY, get_connection, get_db_contract
from ..schemas import UserCreate
from ..security import create_access_token, get_password_hash, verify_password

router = APIRouter()



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
