"""Инициализация таблиц и базовых данных FriendlyMap в PostgreSQL."""

import os
from urllib.parse import urlsplit


def _safe_db_url(db_url: str) -> str:
    parts = urlsplit(db_url)
    if not parts.password:
        return db_url

    host = parts.hostname or "localhost"
    port = f":{parts.port}" if parts.port else ""
    user = parts.username or "user"
    return f"{parts.scheme}://{user}:***@{host}{port}{parts.path}"


def _load_db_api():
    try:
        from .database import BOT_DB_URL, get_connection
    except ModuleNotFoundError:
        raise
    except ImportError:
        from database import BOT_DB_URL, get_connection
    return BOT_DB_URL, get_connection


def _create_tables(get_connection) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS website_users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE,
                    email TEXT UNIQUE,
                    username TEXT NOT NULL,
                    hashed_password TEXT,
                    total_points INTEGER NOT NULL DEFAULT 0,
                    locations_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS website_achievements (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    reward_points INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS website_user_achievements (
                    user_id INTEGER NOT NULL REFERENCES website_users(id) ON DELETE CASCADE,
                    achievement_id TEXT NOT NULL REFERENCES website_achievements(id) ON DELETE CASCADE,
                    unlocked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (user_id, achievement_id)
                );
                """
            )
        conn.commit()


def _seed_achievements(get_connection) -> None:
    achievements = [
        ("facade_expert", "Эксперт по фасадам", 150),
        ("night_watch", "Ночной дозор", 120),
        ("detail_master", "Мастер деталей", 100),
        ("architect_critic", "Архитектурный критик", 250),
        ("first_friend", "Первый друг", 100),
        ("teamwork", "Командная работа", 150),
        ("trendsetter", "Трендсеттер", 250),
    ]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM website_achievements")
            count = cur.fetchone()[0]
            if count > 0:
                print("ℹ️ Достижения уже есть в БД")
                return

            cur.executemany(
                """
                INSERT INTO website_achievements (id, name, reward_points)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                achievements,
            )
        conn.commit()
        print("✅ Достижения добавлены")


def _print_connection_help(error_text: str) -> None:
    print("❌ Не удалось подключиться к PostgreSQL.")

    if "password authentication failed" in error_text:
        print("Причина: неверный логин/пароль PostgreSQL.")
    elif "Connection refused" in error_text:
        print("Причина: PostgreSQL не запущен или недоступен на указанном хосте/порте.")
    elif "does not exist" in error_text:
        print("Причина: указанная база данных не существует.")

    print("Проверьте DATABASE_URL или POSTGRES_HOST/PORT/DB/USER/PASSWORD в .env.")


def main() -> int:
    try:
        BOT_DB_URL, get_connection = _load_db_api()
    except ModuleNotFoundError as exc:
        print("❌ Не хватает Python-зависимостей для запуска init_db.")
        print(f"Причина: {exc}")
        print("Установите зависимости текущим интерпретатором:")
        print("python3 -m pip install -r requirements.txt")
        return 1

    print(f"Используем БД: {_safe_db_url(BOT_DB_URL)}")

    if os.getenv("POSTGRES_PASSWORD", "").strip() == "" and not os.getenv(
        "DATABASE_URL", ""
    ).strip():
        print(
            "⚠️ Внимание: POSTGRES_PASSWORD пустой. Укажите пароль в .env, иначе будет ошибка аутентификации."
        )

    print("Создаём таблицы...")

    try:
        _create_tables(get_connection)
        print("✅ Таблицы созданы")
        _seed_achievements(get_connection)
    except RuntimeError as exc:
        print(f"❌ {exc}")
        return 1
    except Exception as exc:
        _print_connection_help(str(exc))
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
