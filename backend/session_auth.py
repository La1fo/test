import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from fastapi import HTTPException, Request

SESSION_COOKIE_NAME = "fm_session"
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "86400"))
SESSION_SECRET = os.getenv("SECRET_KEY", "")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(data: str) -> bytes:
    pad = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _sign(payload: str) -> str:
    return hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_session_cookie(user_id: int) -> str:
    payload = json.dumps({"user_id": int(user_id), "exp": int(time.time()) + SESSION_TTL_SECONDS}, separators=(",", ":"))
    encoded = _b64(payload.encode())
    return f"{encoded}.{_sign(encoded)}"


def parse_session_cookie(raw: str | None) -> dict[str, Any] | None:
    if not raw or "." not in raw or not SESSION_SECRET:
        return None
    encoded, sig = raw.split(".", 1)
    if not hmac.compare_digest(sig, _sign(encoded)):
        return None
    try:
        payload = json.loads(_unb64(encoded).decode())
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def get_current_user_id(request: Request, required: bool = True) -> int | None:
    payload = parse_session_cookie(request.cookies.get(SESSION_COOKIE_NAME))
    if not payload:
        if required:
            raise HTTPException(status_code=401, detail="Authentication required")
        return None
    return int(payload["user_id"])
