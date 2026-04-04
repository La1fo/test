from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class UserCreate(BaseModel):
    email: str
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Invalid email format")
        return value


class TelegramAuthPayload(BaseModel):
    id: int
    auth_date: int
    hash: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class Coordinates(BaseModel):
    latitude: float
    longitude: float

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        if value < -90 or value > 90:
            raise ValueError("latitude must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        if value < -180 or value > 180:
            raise ValueError("longitude must be between -180 and 180")
        return value


class PhotoMeta(BaseModel):
    temp_id: str = Field(min_length=1, max_length=128)
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=100)
    size_bytes: int = Field(gt=0, le=10 * 1024 * 1024)


class AddLocationBasePayload(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=3000)
    coordinates: Coordinates
    tag_ids: list[str] = Field(default_factory=list)
    photos: list[PhotoMeta] = Field(default_factory=list)

    @field_validator("name", "description")
    @classmethod
    def strip_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value cannot be blank")
        return normalized

    @field_validator("tag_ids")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        cleaned = [tag.strip() for tag in value if tag.strip()]
        if len(cleaned) > 5:
            raise ValueError("no more than 5 tags allowed")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("duplicate tags are not allowed")
        return cleaned

    @field_validator("photos")
    @classmethod
    def validate_photos(cls, value: list[PhotoMeta]) -> list[PhotoMeta]:
        if not value:
            raise ValueError("at least one photo is required")
        if len(value) > 8:
            raise ValueError("no more than 8 photos allowed")
        return value


class AddLocationPreviewRequest(AddLocationBasePayload):
    pass


class AddLocationSubmitRequest(AddLocationBasePayload):
    idempotency_key: str = Field(min_length=8, max_length=128)


class AddLocationPreviewResponse(BaseModel):
    valid: bool
    normalized: AddLocationPreviewRequest
    warnings: list[str] = Field(default_factory=list)


class AddLocationSubmitResponse(BaseModel):
    accepted: bool
    message: str


class AddLocationFormConfigResponse(BaseModel):
    writer_integration_enabled: bool
    max_tags: int
    max_photos: int
    max_photo_size_mb: int
    allowed_photo_mime: list[str]
    tag_catalog: list[dict[str, str]]
    submit_message: str
