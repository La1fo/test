from fastapi import APIRouter, Header, Request

from .. import add_location_contract as contract
from ..add_location_service import get_tag_catalog, save_temp_uploads, submit_location
from ..session_auth import get_current_user_id
from ..schemas import (
    AddLocationFormConfigResponse,
    AddLocationPreviewRequest,
    AddLocationPreviewResponse,
    AddLocationSubmitRequest,
    AddLocationSubmitResponse,
    PhotoUploadRequest,
    PhotoMeta,
)

router = APIRouter()


@router.get("/form-config", response_model=AddLocationFormConfigResponse)
def get_add_location_form_config() -> AddLocationFormConfigResponse:
    try:
        tag_catalog = get_tag_catalog()
    except Exception:
        tag_catalog = [{**item, "category": "Прочее"} for item in contract.TAG_CATALOG]
    return AddLocationFormConfigResponse(
        writer_integration_enabled=contract.INTEGRATION_ENABLED,
        max_tags=contract.MAX_TAGS,
        max_photos=contract.MAX_PHOTOS,
        max_photo_size_mb=contract.MAX_PHOTO_SIZE_MB,
        allowed_photo_mime=contract.ALLOWED_PHOTO_MIME,
        tag_catalog=tag_catalog,
        submit_message=contract.SUBMIT_DISABLED_MESSAGE,
    )


@router.post("/preview", response_model=AddLocationPreviewResponse)
def build_preview(payload: AddLocationPreviewRequest, request: Request) -> AddLocationPreviewResponse:
    get_current_user_id(request, required=True)
    return AddLocationPreviewResponse(
        valid=True,
        normalized=payload,
        warnings=[contract.PREVIEW_WARNING],
    )


@router.post("/upload", response_model=list[PhotoMeta])
def upload_photos(payload: PhotoUploadRequest, request: Request) -> list[PhotoMeta]:
    get_current_user_id(request, required=True)
    return save_temp_uploads(payload.files)


@router.post("/submit", response_model=AddLocationSubmitResponse)
def submit(
    payload: AddLocationSubmitRequest,
    request: Request,
    x_telegram_init_data: str = Header(default="", alias="X-Telegram-Init-Data"),
) -> AddLocationSubmitResponse:
    user_id = get_current_user_id(request, required=True)
    result = submit_location(payload=payload, init_data=x_telegram_init_data, session_user_id=user_id)
    return AddLocationSubmitResponse(
        accepted=True,
        location_id=result.location_id,
        status=result.status,
        duplicate=result.duplicate,
        message="Локация отправлена на модерацию",
    )
