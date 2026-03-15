from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)


class TelegramLogin(BaseModel):
    id: int
    username: str | None = None
    first_name: str | None = None
    auth_date: int
    hash: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str | None
    username: str
    telegram_id: int | None
    total_points: int
    locations_count: int


class AchievementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    reward_points: int


class UserAchievementOut(BaseModel):
    achievement_id: str
    unlocked_at: datetime
