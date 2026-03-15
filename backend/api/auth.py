import os

from fastapi import APIRouter, Body, HTTPException

from ..database import get_connection
from ..schemas import TelegramAuthPayload, UserCreate
from ..security import (
    create_access_token,
    get_password_hash,
    verify_password,
    verify_telegram_auth,
)

router = APIRouter()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


@router.post("/telegram")
def login_telegram(payload: TelegramAuthPayload):
    data = payload.model_dump(exclude_none=True)

    if not verify_telegram_auth(data, TELEGRAM_BOT_TOKEN):
        raise HTTPException(status_code=400, detail="Invalid Telegram auth")

    telegram_id = int(data["id"])
    username = data.get("username") or f"user{str(telegram_id)[-4:]}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM website_users WHERE telegram_id = %s",
                (telegram_id,),
            )
            row = cur.fetchone()

            if row is None:
                cur.execute(
                    """
                    INSERT INTO website_users (telegram_id, username)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (telegram_id, username),
                )
                row = cur.fetchone()
                conn.commit()

    user_id = row[0]
    access_token = create_access_token(data={"sub": str(user_id)})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user_id}


@router.post("/email/register")
def register_email(user: UserCreate):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM website_users WHERE email = %s", (user.email,))
            if cur.fetchone() is not None:
                raise HTTPException(status_code=400, detail="Email already registered")

            hashed_pw = get_password_hash(user.password)
            cur.execute(
                """
                INSERT INTO website_users (email, username, hashed_password)
                VALUES (%s, %s, %s)
                """,
                (user.email, user.username, hashed_pw),
            )
        conn.commit()

    return {"msg": "User created"}


@router.post("/email/login")
def login_email(email: str = Body(...), password: str = Body(...)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, hashed_password FROM website_users WHERE email = %s",
                (email,),
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    user_id, hashed_password = row
    if not hashed_password or not verify_password(password, hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": str(user_id)})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user_id}
