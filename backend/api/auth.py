from fastapi import APIRouter, Body, HTTPException

from ..database import DB_READ_ONLY, get_connection, get_db_contract
from ..schemas import UserCreate, UsernameUserCreate
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


def _normalize_username(username: str) -> str:
    return username.strip().lstrip("@")


def _validate_username(username: str) -> str:
    normalized = _normalize_username(username)
    if len(normalized) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(normalized) > 50:
        raise HTTPException(status_code=400, detail="Username must be no more than 50 characters")
    return normalized


def _find_user_by_username(cur, username: str):
    users_view = get_db_contract().auth_users_view
    normalized = _normalize_username(username)
    cur.execute(
        f"""
        SELECT user_id, hashed_password
        FROM {users_view}
        WHERE LOWER(username) = LOWER(%s)
        LIMIT 1
        """,
        (normalized,),
    )
    return cur.fetchone()


def _insert_user_account(*, username: str, password: str, email: str | None = None) -> int:
    if DB_READ_ONLY:
        raise HTTPException(status_code=503, detail="Registration disabled in read-only DB mode")
    normalized_username = _validate_username(username)
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(%s) LIMIT 1", (normalized_username,))
                if cur.fetchone():
                    raise HTTPException(status_code=409, detail="Username already exists")
                if email is not None:
                    cur.execute("SELECT id FROM users WHERE LOWER(email) = %s LIMIT 1", (_normalize_email(email),))
                    if cur.fetchone():
                        raise HTTPException(status_code=409, detail="Email already exists")
                cols = _users_columns(cur)
                required_defaults = {
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
                if email is not None:
                    required_defaults["email"] = _normalize_email(email)
                fields = ["username"]
                values: list[object] = [normalized_username]
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


def register_username_account(*, username: str, password: str) -> int:
    return _insert_user_account(username=username, password=password)


def register_email_account(*, username: str, email: str, password: str) -> int:
    normalized_email = _normalize_email(email)
    if "@" not in normalized_email or normalized_email.startswith("@") or normalized_email.endswith("@"):
        raise HTTPException(status_code=400, detail="Invalid email format")
    return _insert_user_account(username=username, email=normalized_email, password=password)




@router.post("/register")
def register_username(user: UsernameUserCreate):
    user_id = register_username_account(username=user.username, password=user.password)
    access_token = create_access_token(data={"sub": str(user_id)})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user_id}


@router.post("/email/register")
def register_email(user: UserCreate):
    user_id = register_email_account(username=user.username, email=user.email, password=user.password)
    access_token = create_access_token(data={"sub": str(user_id)})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user_id}


def login_username(username: str = Body(...), password: str = Body(...)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            row = _find_user_by_username(cur, username)

    if row is None:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    user_id, hashed_password = row
    if not hashed_password or not verify_password(password, hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": str(user_id)})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user_id}


@router.post("/login")
def login_username_route(username: str = Body(...), password: str = Body(...)):
    return login_username(username=username, password=password)


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
