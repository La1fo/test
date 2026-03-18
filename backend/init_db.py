from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from backend.database import engine
from backend.models import Achievement, Base

print("Создаём таблицы...")

try:
    Base.metadata.create_all(bind=engine)
except OperationalError as exc:
    raise SystemExit(
        "❌ Не удалось подключиться к PostgreSQL. Проверьте DATABASE_URL (логин/пароль/хост/порт/БД)."
    ) from exc

print("✅ Таблицы созданы")

Session = sessionmaker(bind=engine)
db = Session()

try:
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
finally:
    db.close()
