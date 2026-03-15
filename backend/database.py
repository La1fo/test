from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DEFAULT_DB_URL = "sqlite:///./friendlymap.db"


def _resolve_db_url() -> str:
    """Возвращает URL БД из окружения c корректным fallback."""
    db_url = os.getenv("DATABASE_URL") or os.getenv("DB_URL") or DEFAULT_DB_URL
    return db_url.strip()


BOT_DB_URL = _resolve_db_url()

bot_engine = create_engine(BOT_DB_URL)

BotSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bot_engine)


def get_bot_db():
    db = BotSessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_website_tables():
    try:
        from models.database_models import Base

        Base.metadata.create_all(bind=bot_engine)
        print("Все таблицы для сайта созданы/проверены")

        from sqlalchemy import inspect

        inspector = inspect(bot_engine)
        tables = inspector.get_table_names()
        website_tables = [t for t in tables if t.startswith("website_")]
        print(f"Таблицы сайта: {website_tables}")

    except ImportError as e:
        print(f"Ошибка импорта моделей: {e}")
    except Exception as e:
        print(f"Предупреждение при создании таблиц: {e}")
