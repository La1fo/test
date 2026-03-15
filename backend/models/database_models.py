from dataclasses import dataclass
from datetime import datetime


@dataclass
class WebsiteUser:
    id: int
    telegram_id: int | None
    email: str | None
    username: str
    hashed_password: str | None
    total_points: int = 0
    locations_count: int = 0

    def get_current_rank_and_points(self):
        total = self.total_points
        if total >= 2500:
            return "Мастер-картограф", total
        if total >= 2000:
            return "Картограф", total
        if total >= 1500:
            return "Первооткрыватель", total - 1500
        if total >= 1000:
            return "Путешественник", total - 1000
        if total >= 600:
            return "Исследователь 1", (total - 600) % 100
        if total >= 300:
            return "Исследователь 2", (total - 300) % 100
        if total >= 0:
            return "Исследователь 3", total % 100
        return "Новичок", total


@dataclass
class Achievement:
    id: str
    name: str
    description: str | None = None
    reward_points: int = 0


@dataclass
class UserAchievement:
    user_id: int
    achievement_id: str
    unlocked_at: datetime
