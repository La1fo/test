"""Инициализация таблиц и базовых данных FriendlyMap."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(__file__))


REQUIREMENTS_PATH = Path(__file__).resolve().parent.parent / "requirements.txt"


def _safe_db_url(db_url: str) -> str:
    parts = urlsplit(db_url)
    if not parts.password:
        return db_url

    host = parts.hostname or "localhost"
    port = f":{parts.port}" if parts.port else ""
    user = parts.username or "user"
    return f"{parts.scheme}://{user}:***@{host}{port}{parts.path}"


def _install_dependencies() -> bool:
    if not REQUIREMENTS_PATH.exists():
        print("❌ Файл requirements.txt не найден, автоустановка зависимостей невозможна.")
        return False

    print("ℹ️ Пробуем установить недостающие зависимости...")
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)]

    try:
        result = subprocess.run(cmd, check=False)
    except OSError as exc:
        print(f"❌ Не удалось запустить pip: {exc}")
        return False

    if result.returncode != 0:
        print("❌ Автоустановка зависимостей завершилась ошибкой.")
        print(f"Запустите вручную: {sys.executable} -m pip install -r {REQUIREMENTS_PATH}")
        return False

    print("✅ Зависимости установлены.")
    return True


def _load_db_modules():
    """Ленивая загрузка модулей БД с автоустановкой зависимостей при необходимости."""
    try:
        from sqlalchemy.exc import OperationalError
        from sqlalchemy.orm import sessionmaker

        from database import BOT_DB_URL, bot_engine
        from models.database_models import Achievement, Base

        return OperationalError, sessionmaker, BOT_DB_URL, bot_engine, Achievement, Base
    except ModuleNotFoundError as exc:
        print("❌ Не хватает Python-зависимостей для запуска init_db.")
        print(f"Причина: {exc}")

        auto_install = os.getenv("AUTO_INSTALL_DEPS", "1").strip() not in {"0", "false", "False"}
        if not auto_install:
            print("Автоустановка отключена (AUTO_INSTALL_DEPS=0).")
            print(f"Установите вручную: {sys.executable} -m pip install -r {REQUIREMENTS_PATH}")
            return None

        if not _install_dependencies():
            return None

        # Повторяем импорт после установки
        from sqlalchemy.exc import OperationalError
        from sqlalchemy.orm import sessionmaker

        from database import BOT_DB_URL, bot_engine
        from models.database_models import Achievement, Base

        return OperationalError, sessionmaker, BOT_DB_URL, bot_engine, Achievement, Base
    except RuntimeError as exc:
        print("❌ Ошибка инициализации БД.")
        print(exc)
        return None


def main() -> int:
    loaded = _load_db_modules()
    if loaded is None:
        return 1

    OperationalError, sessionmaker, BOT_DB_URL, bot_engine, Achievement, Base = loaded

    print(f"Используем БД: {_safe_db_url(BOT_DB_URL)}")

    if os.getenv("POSTGRES_PASSWORD", "").strip() == "" and not os.getenv(
        "DATABASE_URL", ""
    ).strip():
        print(
            "⚠️ Внимание: POSTGRES_PASSWORD пустой. Укажите пароль в .env, иначе будет ошибка аутентификации."
        )

    print("Создаём таблицы...")

    try:
        Base.metadata.create_all(bind=bot_engine)
        print("✅ Таблицы созданы")
    except OperationalError as exc:
        error_text = str(getattr(exc, "orig", exc))
        print("❌ Не удалось подключиться к PostgreSQL.")

        if "password authentication failed" in error_text:
            print("Причина: неверный логин/пароль PostgreSQL.")
        elif "Connection refused" in error_text:
            print("Причина: PostgreSQL не запущен или недоступен на указанном хосте/порте.")
        elif "does not exist" in error_text:
            print("Причина: указанная база данных не существует.")

        print("Проверьте DATABASE_URL или POSTGRES_HOST/PORT/DB/USER/PASSWORD в .env.")
        return 1

    session_factory = sessionmaker(bind=bot_engine)
    db = session_factory()

    try:
        if db.query(Achievement).count() == 0:
            print("Заполняем таблицу достижений...")
            achievements = [
                Achievement(id="facade_expert", name="Эксперт по фасадам", reward_points=150),
                Achievement(id="night_watch", name="Ночной дозор", reward_points=120),
                Achievement(id="detail_master", name="Мастер деталей", reward_points=100),
                Achievement(
                    id="architect_critic",
                    name="Архитектурный критик",
                    reward_points=250,
                ),
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
