import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 часа

if len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY должен быть задан и содержать не менее 32 символов")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_telegram_auth(data: dict, bot_token: str) -> bool:
    """Проверка подписи Telegram Login Widget + ограничение по времени (anti-replay)."""
    if not bot_token:
        return False

    payload = data.copy()
    check_hash = payload.pop("hash", None)
    if not check_hash:
        return False

    auth_date = payload.get("auth_date")
    try:
        auth_dt = datetime.fromtimestamp(int(auth_date), tz=timezone.utc)
    except (TypeError, ValueError):
        return False

    if datetime.now(timezone.utc) - auth_dt > timedelta(minutes=10):
        return False

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    expected_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_hash, check_hash)
