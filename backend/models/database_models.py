# backend/models/database_models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class WebsiteUser(Base):
    __tablename__ = "website_users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=True, index=True)
    email = Column(String, unique=True, nullable=True, index=True)
    username = Column(String, index=True)
    hashed_password = Column(String, nullable=True)
    total_points = Column(Integer, default=0)  # ← общее количество заработанных очков
    locations_count = Column(Integer, default=0)

    def get_current_rank_and_points(self):
        """Возвращает (ранг, текущие_очки_в_ранге)"""
        total = self.total_points
        if total >= 2500:
            return "Мастер-картограф", total
        elif total >= 2000:
            return "Картограф", total
        elif total >= 1500:
            return "Первооткрыватель", total - 1500
        elif total >= 1000:
            return "Путешественник", total - 1000
        elif total >= 600:
            return "Исследователь 1", (total - 600) % 100
        elif total >= 300:
            return "Исследователь 2", (total - 300) % 100
        elif total >= 0:
            return "Исследователь 3", total % 100
        return "Новичок", total

class Achievement(Base):
    __tablename__ = "website_achievements"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    reward_points = Column(Integer, default=0)

class UserAchievement(Base):
    __tablename__ = "website_user_achievements"
    user_id = Column(Integer, ForeignKey("website_users.id"), primary_key=True)
    achievement_id = Column(String, ForeignKey("website_achievements.id"), primary_key=True)
    unlocked_at = Column(DateTime, default=datetime.utcnow)