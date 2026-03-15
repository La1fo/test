# backend/init_db.py
import os
import sys
from urllib.parse import urlsplit

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(__file__))

from database import BOT_DB_URL, bot_engine
from models.database_models import Achievement, Base


def _safe_db_url(db_url: str) -> str:
    parts = urlsplit(db_url)
    if not parts.password:
        return db_url
    netloc = f"{parts.username}:***@{parts.hostname}:{parts.port}"
    return f"{parts.scheme}://{netloc}{parts.path}"


print(f"Используем БД: {_safe_db_url(BOT_DB_URL)}")

if os.getenv("POSTGRES_PASSWORD", "").strip() == "" and not os.getenv("DATABASE_URL", "").strip():
    print("⚠️ Внимание: POSTGRES_PASSWORD пустой. Укажите пароль в .env, иначе будет ошибка аутентификации.")

print("Создаём таблицы...")

try:
    Base.metadata.create_all(bind=bot_engine)
    print("✅ Таблицы созданы")
except OperationalError as e:
    error_text = str(e.orig)
    print("❌ Не удалось подключиться к PostgreSQL.")

    if "password authentication failed" in error_text:
        print("Причина: неверный логин/пароль PostgreSQL.")
    elif "Connection refused" in error_text:
        print("Причина: PostgreSQL не запущен или недоступен на указанном хосте/порте.")
    elif "does not exist" in error_text:
        print("Причина: указанная база данных не существует.")

    print("Проверьте DATABASE_URL или POSTGRES_HOST/PORT/DB/USER/PASSWORD в .env.")
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
