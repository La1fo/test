from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class WebsiteUser(Base):
    __tablename__ = "website_users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    username = Column(String(80), nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    total_points = Column(Integer, default=0, nullable=False)
    locations_count = Column(Integer, default=0, nullable=False)

    achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")

    def get_current_rank_and_points(self):
        total = max(0, self.total_points or 0)
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
        return "Исследователь 3", total % 100


class Achievement(Base):
    __tablename__ = "website_achievements"

    id = Column(String(100), primary_key=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    reward_points = Column(Integer, default=0, nullable=False)

    users = relationship("UserAchievement", back_populates="achievement", cascade="all, delete-orphan")


class UserAchievement(Base):
    __tablename__ = "website_user_achievements"

    user_id = Column(Integer, ForeignKey("website_users.id", ondelete="CASCADE"), primary_key=True)
    achievement_id = Column(String(100), ForeignKey("website_achievements.id", ondelete="CASCADE"), primary_key=True)
    unlocked_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("WebsiteUser", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="users")
