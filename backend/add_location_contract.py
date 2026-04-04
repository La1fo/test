"""Canonical constants for reader-side add-location integration shell.

This module centralizes limits and catalog defaults so UI/API/tests stay in sync.
"""

INTEGRATION_ENABLED = True
MAX_TAGS = 5
MAX_PHOTOS = 8
MAX_PHOTO_SIZE_MB = 10
MAX_PHOTO_SIZE_BYTES = MAX_PHOTO_SIZE_MB * 1024 * 1024
ALLOWED_PHOTO_MIME = ["image/jpeg", "image/png", "image/webp"]

TAG_CATALOG = [
    {"id": "ramp", "label": "Пандус"},
    {"id": "parking", "label": "Парковка"},
    {"id": "toilet", "label": "Туалет"},
    {"id": "entrance", "label": "Вход"},
    {"id": "elevator", "label": "Лифт"},
    {"id": "staff_help", "label": "Помощь персонала"},
    {"id": "navigation", "label": "Навигация"},
]

SUBMIT_DISABLED_MESSAGE = (
    "Проверьте данные и отправьте локацию на модерацию."
)

PREVIEW_WARNING = "После отправки локация будет создана со статусом pending и уйдёт на модерацию."
