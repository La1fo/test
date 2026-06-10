import os
import re
import shutil
import uuid
import base64
import binascii
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException

from . import add_location_contract as contract
from .database import DB_READ_ONLY, get_connection
from .schemas import AddLocationSubmitRequest, PhotoMeta, PhotoUploadItem

MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "/workspace/test/media")).resolve()
MAX_BYTES = contract.MAX_PHOTO_SIZE_BYTES
SAFE_TEMP_ID = re.compile(r"^[a-f0-9\-]{8,64}$")


@dataclass
class SubmitResult:
    location_id: int
    status: str
    duplicate: bool


def _ensure_write_allowed() -> None:
    if DB_READ_ONLY:
        raise HTTPException(status_code=503, detail="Write operations are disabled in read-only DB mode")


def _safe_filename(name: str) -> str:
    basename = os.path.basename(name).strip().replace(" ", "_")
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "", basename)
    return cleaned[:120] or "photo.bin"


def _tmp_dir() -> Path:
    p = MEDIA_ROOT / "tmp"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _location_dir(location_id: int) -> Path:
    p = MEDIA_ROOT / "locations" / str(location_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_temp_uploads(files: list[PhotoUploadItem]) -> list[PhotoMeta]:
    _ensure_write_allowed()
    if not files:
        raise HTTPException(status_code=400, detail="At least one photo is required")
    if len(files) > contract.MAX_PHOTOS:
        raise HTTPException(status_code=400, detail=f"No more than {contract.MAX_PHOTOS} files allowed")

    tmp = _tmp_dir()
    result: list[PhotoMeta] = []

    for file in files:
        mime = (file.mime_type or "").lower()
        if mime not in contract.ALLOWED_PHOTO_MIME:
            raise HTTPException(status_code=400, detail=f"Unsupported mime type: {mime or 'unknown'}")
        try:
            content = base64.b64decode(file.content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"Invalid base64 photo payload: {exc}") from exc
        if not content:
            raise HTTPException(status_code=400, detail="Empty file is not allowed")
        if len(content) > MAX_BYTES:
            raise HTTPException(status_code=400, detail="File exceeds max allowed size")

        temp_id = str(uuid.uuid4())
        safe_name = _safe_filename(file.filename or "photo.bin")
        path = tmp / f"{temp_id}-{safe_name}"
        path.write_bytes(content)

        result.append(
            PhotoMeta(
                temp_id=temp_id,
                filename=safe_name,
                mime_type=mime,
                size_bytes=len(content),
            )
        )

    return result


def _ensure_idempotency_table(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS site_submission_idempotency (
          id BIGSERIAL PRIMARY KEY,
          idempotency_key TEXT NOT NULL,
          user_id BIGINT NOT NULL,
          location_id BIGINT,
          created_at TIMESTAMPTZ DEFAULT NOW(),
          UNIQUE (idempotency_key, user_id)
        )
        """
    )
    cur.execute("ALTER TABLE site_submission_idempotency ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_site_submission_idempotency_key_user
        ON site_submission_idempotency (idempotency_key, user_id)
        WHERE user_id IS NOT NULL
        """
    )



def _resolve_user_by_id(cur, user_id: int) -> int:
    cur.execute("SELECT id FROM users WHERE id = %s LIMIT 1", (user_id,))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=403, detail="Authenticated user not found in users table")
    return int(row[0])


def _resolve_db_tags(cur, tag_ids: list[str]) -> list[int]:
    if not tag_ids:
        return []
    resolved: list[int] = []
    for tag in tag_ids:
        cur.execute("SELECT id FROM tags WHERE slug = %s OR code = %s OR CAST(id AS TEXT) = %s LIMIT 1", (tag, tag, tag))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=400, detail=f"Unknown tag: {tag}")
        resolved.append(int(row[0]))
    return list(dict.fromkeys(resolved))


def _pending_location(cur, user_id: int, payload: AddLocationSubmitRequest) -> int:
    cur.execute(
        """
        INSERT INTO locations (user_id, name, description, latitude, longitude, status)
        VALUES (%s, %s, %s, %s, %s, 'pending')
        RETURNING id
        """,
        (
            user_id,
            payload.name,
            payload.description,
            payload.coordinates.latitude,
            payload.coordinates.longitude,
        ),
    )
    location_id = int(cur.fetchone()[0])
    cur.execute("UPDATE users SET moderation_locations = COALESCE(moderation_locations, 0) + 1 WHERE id = %s", (user_id,))
    return location_id


def _insert_location_tags(cur, location_id: int, tag_ids: list[int]) -> None:
    for tag_id in tag_ids:
        cur.execute(
            """
            INSERT INTO location_tags (location_id, tag_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (location_id, tag_id),
        )


def _find_temp_file(temp_id: str) -> Path:
    if not SAFE_TEMP_ID.match(temp_id):
        raise HTTPException(status_code=400, detail="Invalid temp photo id")
    candidates = list(_tmp_dir().glob(f"{temp_id}-*"))
    if not candidates:
        raise HTTPException(status_code=400, detail=f"Temp photo not found: {temp_id}")
    return candidates[0]


def _store_location_photo(cur, location_id: int, photo: PhotoMeta, order_index: int) -> str:
    src = _find_temp_file(photo.temp_id)
    dest_name = f"{order_index:02d}-{_safe_filename(photo.filename)}"
    dest = _location_dir(location_id) / dest_name
    shutil.move(str(src), dest)
    rel_path = str(dest.relative_to(MEDIA_ROOT))

    try:
        cur.execute(
            """
            INSERT INTO photos (location_id, file_id, description, order_index, storage_type, storage_path, mime_type, original_name, size_bytes)
            VALUES (%s, %s, %s, %s, 'uploaded', %s, %s, %s, %s)
            """,
            (location_id, f"uploaded:{rel_path}", None, order_index, rel_path, photo.mime_type, photo.filename, photo.size_bytes),
        )
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    return str(dest)


def submit_location(payload: AddLocationSubmitRequest, session_user_id: int | None = None) -> SubmitResult:
    _ensure_write_allowed()
    if session_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    idempotency_user_id = int(session_user_id)

    moved_files: list[str] = []
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                _ensure_idempotency_table(cur)
                cur.execute(
                    "SELECT location_id FROM site_submission_idempotency WHERE idempotency_key = %s AND user_id = %s",
                    (payload.idempotency_key, idempotency_user_id),
                )
                row = cur.fetchone()
                if row and row[0]:
                    conn.commit()
                    return SubmitResult(location_id=int(row[0]), status="pending", duplicate=True)

                user_id = _resolve_user_by_id(cur, idempotency_user_id)
                db_tag_ids = _resolve_db_tags(cur, payload.tag_ids)
                location_id = _pending_location(cur, user_id, payload)
                _insert_location_tags(cur, location_id, db_tag_ids)

                for idx, photo in enumerate(payload.photos):
                    moved_files.append(_store_location_photo(cur, location_id, photo, idx))

                cur.execute(
                    """
                    INSERT INTO site_submission_idempotency (idempotency_key, user_id, location_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (idempotency_key, user_id)
                    DO UPDATE SET location_id = EXCLUDED.location_id
                    """,
                    (payload.idempotency_key, idempotency_user_id, location_id),
                )

            conn.commit()
            return SubmitResult(location_id=location_id, status="pending", duplicate=False)
        except Exception:
            conn.rollback()
            for file_path in moved_files:
                path = Path(file_path)
                if path.exists():
                    path.unlink(missing_ok=True)
            raise


def resolve_photo_url(file_id: str | None, storage_type: str | None, storage_path: str | None) -> str | None:
    if storage_type == "uploaded" and storage_path:
        return f"/media/{storage_path}"
    if file_id:
        return f"/api/photos/{file_id}"
    return None


def get_tag_catalog() -> list[dict[str, str]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, category, slug FROM tags ORDER BY category, name")
            rows = cur.fetchall()
    return [
        {"id": str(row[3] or row[0]), "label": row[1], "category": row[2] or "Без категории"}
        for row in rows
    ]
