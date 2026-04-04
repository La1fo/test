from fastapi import APIRouter, HTTPException

from .. import add_location_contract as contract
from ..schemas import (
    AddLocationFormConfigResponse,
    AddLocationPreviewRequest,
    AddLocationPreviewResponse,
    AddLocationSubmitRequest,
    AddLocationSubmitResponse,
)

router = APIRouter()

@router.get("/form-config", response_model=AddLocationFormConfigResponse)
def get_add_location_form_config() -> AddLocationFormConfigResponse:
    return AddLocationFormConfigResponse(
        writer_integration_enabled=contract.INTEGRATION_ENABLED,
        max_tags=contract.MAX_TAGS,
        max_photos=contract.MAX_PHOTOS,
        max_photo_size_mb=contract.MAX_PHOTO_SIZE_MB,
        allowed_photo_mime=contract.ALLOWED_PHOTO_MIME,
        tag_catalog=contract.TAG_CATALOG,
        submit_message=contract.SUBMIT_DISABLED_MESSAGE,
    )


@router.post("/preview", response_model=AddLocationPreviewResponse)
def build_preview(payload: AddLocationPreviewRequest) -> AddLocationPreviewResponse:
    return AddLocationPreviewResponse(
        valid=True,
        normalized=payload,
        warnings=[contract.PREVIEW_WARNING],
    )


@router.post("/submit", response_model=AddLocationSubmitResponse)
def submit_stub(payload: AddLocationSubmitRequest) -> AddLocationSubmitResponse:
    _ = payload
    raise HTTPException(
        status_code=501,
        detail=contract.SUBMIT_NOT_CONNECTED_DETAIL,
    )
