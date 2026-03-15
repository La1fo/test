# backend/init_db.py
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from database import bot_engine
from models.database_models import Base, Achievement
from sqlalchemy.orm import sessionmaker

# Создаём таблицы
print("Создаём таблицы...")
Base.metadata.create_all(bind=bot_engine)
print("✅ Таблицы созданы")

# Заполняем таблицу достижений (пример)
Session = sessionmaker(bind=bot_engine)
db = Session()

# Проверяем, не заполнена ли уже
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