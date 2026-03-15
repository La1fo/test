import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 часа

if len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY должен быть задан и содержать не менее 32 символов")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _sign(message: bytes) -> str:
    digest = hmac.new(SECRET_KEY.encode("utf-8"), message, hashlib.sha256).digest()
    return _b64url(digest)


def get_password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return f"pbkdf2_sha256$200000${salt.hex()}${dk.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        scheme, rounds, salt_hex, hash_hex = hashed_password.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(rounds),
        )
        return hmac.compare_digest(derived.hex(), hash_hex)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = data.copy()
    payload["exp"] = int(expire.timestamp())

    header = {"alg": ALGORITHM, "typ": "JWT"}
    encoded_header = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = _sign(signing_input)
    return f"{encoded_header}.{encoded_payload}.{signature}"


def verify_telegram_auth(data: dict, bot_token: str) -> bool:
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
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_hash, check_hash)
