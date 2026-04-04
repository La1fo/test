from fastapi import APIRouter, HTTPException

from ..schemas import (
    AddLocationFormConfigResponse,
    AddLocationPreviewRequest,
    AddLocationPreviewResponse,
    AddLocationSubmitRequest,
    AddLocationSubmitResponse,
)

router = APIRouter()

# Integration-shell catalog for writer-side handoff.
DEFAULT_TAG_CATALOG = [
    {"id": "ramp", "label": "Пандус"},
    {"id": "parking", "label": "Парковка"},
    {"id": "toilet", "label": "Туалет"},
    {"id": "entrance", "label": "Вход"},
    {"id": "elevator", "label": "Лифт"},
    {"id": "staff_help", "label": "Помощь персонала"},
    {"id": "navigation", "label": "Навигация"},
]


@router.get("/form-config", response_model=AddLocationFormConfigResponse)
def get_add_location_form_config() -> AddLocationFormConfigResponse:
    return AddLocationFormConfigResponse(
        writer_integration_enabled=False,
        max_tags=5,
        max_photos=8,
        max_photo_size_mb=10,
        allowed_photo_mime=["image/jpeg", "image/png", "image/webp"],
        tag_catalog=DEFAULT_TAG_CATALOG,
        submit_message=(
            "Форма готова к интеграции с writer-side backend. "
            "Финальная отправка в shared БД пока отключена на reader-side сайте."
        ),
    )


@router.post("/preview", response_model=AddLocationPreviewResponse)
def build_preview(payload: AddLocationPreviewRequest) -> AddLocationPreviewResponse:
    return AddLocationPreviewResponse(
        valid=True,
        normalized=payload,
        warnings=[
            "Это preview в integration-shell режиме: запись в shared БД здесь не выполняется.",
        ],
    )


@router.post("/submit", response_model=AddLocationSubmitResponse)
def submit_stub(payload: AddLocationSubmitRequest) -> AddLocationSubmitResponse:
    _ = payload
    raise HTTPException(
        status_code=501,
        detail=(
            "Writer-side integration not connected in this repository. "
            "Use writer backend submission service when available."
        ),
    )
