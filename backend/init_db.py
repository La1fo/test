# backend/init_db.py
import os
import sys

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(__file__))

from database import BOT_DB_URL, bot_engine
from models.database_models import Achievement, Base

print(f"Используем БД: {BOT_DB_URL}")
print("Создаём таблицы...")

try:
    Base.metadata.create_all(bind=bot_engine)
    print("✅ Таблицы созданы")
except OperationalError as e:
    print("❌ Не удалось подключиться к базе данных.")
    print(
        "Проверьте DATABASE_URL/DB_URL (логин, пароль, хост и порт) в .env или переменных окружения."
    )
    raise SystemExit(1) from e

Session = sessionmaker(bind=bot_engine)
db = Session()

if db.query(Achievement).count() == 0:
    print("Заполняем таблицу достижений...")
    achievements = [
        Achievement(id="facade_expert", name="Эксперт по фасадам", reward_points=150),
        Achievement(id="night_watch", name="Ночной дозор", reward_points=120),
        Achievement(id="detail_master", name="Мастер деталей", reward_points=100),
        Achievement(id="architect_critic", name="Архитектурный критик", reward_points=250),
        Achievement(id="first_friend", name="Первый друг", reward_points=100),
        Achievement(id="teamwork", name="Командная работа", reward_points=150),
        Achievement(id="trendsetter", name="Трендсеттер", reward_points=250),
    ]
    db.add_all(achievements)
    db.commit()
    print("✅ Достижения добавлены")
else:
    print("ℹ️ Достижения уже есть в БД")

db.close()
