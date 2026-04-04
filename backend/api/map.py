from fastapi import APIRouter

from ..add_location_service import resolve_photo_url
from ..database import get_connection

router = APIRouter()


@router.get("/locations")
def approved_locations():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT l.id, l.name, l.description, l.latitude, l.longitude,
                       p.file_id, p.storage_type, p.storage_path,
                       COALESCE(string_agg(t.name, ', '), '') AS tags
                FROM locations l
                LEFT JOIN photos p ON p.location_id = l.id
                LEFT JOIN location_tags lt ON lt.location_id = l.id
                LEFT JOIN tags t ON t.id = lt.tag_id
                WHERE l.status = 'approved'
                GROUP BY l.id, l.name, l.description, l.latitude, l.longitude, p.file_id, p.storage_type, p.storage_path
                ORDER BY l.id DESC
                LIMIT 500
                """
            )
            rows = cur.fetchall()

    return [
        {
            "id": int(r[0]),
            "name": r[1],
            "description": r[2] or "",
            "latitude": float(r[3]),
            "longitude": float(r[4]),
            "tags": [t.strip() for t in (r[8] or "").split(",") if t.strip()],
            "photo_url": resolve_photo_url(r[5], r[6], r[7]),
        }
        for r in rows
    ]
