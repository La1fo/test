from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

BOT_DB_URL = os.getenv("DB_URL", "postgresql://website_user:uzEIV7IPZ2aE2Ek6Gr@46.32.185.61:5432/telegram_bot_db ")

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
        website_tables = [t for t in tables if t.startswith('website_')]
        print(f"Таблицы сайта: {website_tables}")
        
    except ImportError as e:
        print(f"Ошибка импорта моделей: {e}")
    except Exception as e:
        print(f"Предупреждение при создании таблиц: {e}")