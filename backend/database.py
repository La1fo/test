import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()


def _build_postgres_url() -> str:
    """Собирает PostgreSQL URL из DATABASE_URL/DB_URL или отдельных POSTGRES_* переменных."""
    explicit_url = (os.getenv("DATABASE_URL") or os.getenv("DB_URL") or "").strip()
    if explicit_url:
        return explicit_url

    host = os.getenv("POSTGRES_HOST", "localhost").strip()
    port = os.getenv("POSTGRES_PORT", "5432").strip()
    database = os.getenv("POSTGRES_DB", "friendlymap").strip()
    user = quote_plus(os.getenv("POSTGRES_USER", "postgres").strip())
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", "").strip())

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


BOT_DB_URL = _build_postgres_url()

bot_engine = create_engine(
    BOT_DB_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
)

BotSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bot_engine)

# Совместимость с API-модулями
SessionLocal = BotSessionLocal


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

    except ImportError as e:
        print(f"Ошибка импорта моделей: {e}")
    except Exception as e:
        print(f"Предупреждение при создании таблиц: {e}")
