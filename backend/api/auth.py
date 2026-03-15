import os

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import WebsiteUser
from ..schemas import TelegramAuthPayload, UserCreate
from ..security import (
    create_access_token,
    get_password_hash,
    verify_password,
    verify_telegram_auth,
)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


@router.post("/telegram")
def login_telegram(payload: TelegramAuthPayload, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_none=True)

    if not verify_telegram_auth(data, TELEGRAM_BOT_TOKEN):
        raise HTTPException(status_code=400, detail="Invalid Telegram auth")

    telegram_id = int(data["id"])
    username = data.get("username") or f"user{str(telegram_id)[-4:]}"

    user = db.query(WebsiteUser).filter(WebsiteUser.telegram_id == telegram_id).first()
    if not user:
        user = WebsiteUser(telegram_id=telegram_id, username=username)
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id}


@router.post("/email/register")
def register_email(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(WebsiteUser).filter(WebsiteUser.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = get_password_hash(user.password)
    db_user = WebsiteUser(
        email=user.email,
        username=user.username,
        hashed_password=hashed_pw,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"msg": "User created"}


@router.post("/email/login")
def login_email(
    email: str = Body(...),
    password: str = Body(...),
    db: Session = Depends(get_db),
):
    user = db.query(WebsiteUser).filter(WebsiteUser.email == email).first()
    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id}
