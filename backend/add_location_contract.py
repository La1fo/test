"""Canonical constants for reader-side add-location integration shell.

This module centralizes limits and catalog defaults so UI/API/tests stay in sync.
"""

INTEGRATION_ENABLED = False
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
    "Форма готова к интеграции с writer-side backend. "
    "Финальная отправка в shared БД пока отключена на reader-side сайте."
)

PREVIEW_WARNING = "Это preview в integration-shell режиме: запись в shared БД здесь не выполняется."
SUBMIT_NOT_CONNECTED_DETAIL = (
    "Writer-side integration not connected in this repository. "
    "Use writer backend submission service when available."
)
