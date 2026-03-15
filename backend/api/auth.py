import os

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import WebsiteUser
from ..schemas import TelegramLogin, Token, UserCreate, UserLogin
from ..security import create_access_token, get_password_hash, verify_password, verify_telegram_auth

router = APIRouter(prefix="/api/auth", tags=["auth"])

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


@router.post("/telegram", response_model=Token)
def login_telegram(data: TelegramLogin, db: Session = Depends(get_db)):
    payload = data.model_dump()
    if not verify_telegram_auth(payload, TELEGRAM_BOT_TOKEN):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Telegram auth")

    telegram_id = payload["id"]
    username = (payload.get("username") or f"{payload.get('first_name', 'user')}{str(telegram_id)[-4:]}").strip()[:80]

    user = db.query(WebsiteUser).filter(WebsiteUser.telegram_id == telegram_id).first()
    if not user:
        user = WebsiteUser(telegram_id=telegram_id, username=username)
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            user = db.query(WebsiteUser).filter(WebsiteUser.telegram_id == telegram_id).first()
            if not user:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to create Telegram user")
        else:
            db.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id}


@router.post("/email/register", status_code=status.HTTP_201_CREATED)
def register_email(user: UserCreate, db: Session = Depends(get_db)):
    email = user.email.lower().strip()
    username = user.username.strip()

    db_user = WebsiteUser(
        email=email,
        username=username,
        hashed_password=get_password_hash(user.password),
    )
    db.add(db_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid registration data")

    return {"message": "User created"}


@router.post("/email/login", response_model=Token)
def login_email(credentials: UserLogin = Body(...), db: Session = Depends(get_db)):
    email = credentials.email.lower().strip()
    user = db.query(WebsiteUser).filter(WebsiteUser.email == email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id}
