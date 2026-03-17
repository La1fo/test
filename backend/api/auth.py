import os

from fastapi import APIRouter, Body, HTTPException

from ..database import get_connection, get_db_contract
from ..schemas import TelegramAuthPayload, UserCreate
from ..security import create_access_token, verify_password, verify_telegram_auth

router = APIRouter()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


@router.post("/telegram")
def login_telegram(payload: TelegramAuthPayload):
    data = payload.model_dump(exclude_none=True)

    if not verify_telegram_auth(data, TELEGRAM_BOT_TOKEN):
        raise HTTPException(status_code=400, detail="Invalid Telegram auth")

    telegram_id = int(data["id"])
    users_view = get_db_contract().public_users_view

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
    _ = user
    raise HTTPException(
        status_code=403,
        detail="Registration is disabled on site reader service. Use writer-side registration flow.",
    )


@router.post("/email/login")
def login_email(email: str = Body(...), password: str = Body(...)):
    users_view = get_db_contract().public_users_view

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT user_id, hashed_password FROM {users_view} WHERE email = %s",
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
