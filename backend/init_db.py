"""Проверка подключения к уже созданной базе FriendlyMap в PostgreSQL."""

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
        from .database import BOT_DB_URL, DB_READ_ONLY, resolve_table_mapping
    except ModuleNotFoundError:
        raise
    except ImportError:
        from database import BOT_DB_URL, DB_READ_ONLY, resolve_table_mapping
    return BOT_DB_URL, DB_READ_ONLY, resolve_table_mapping


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
        BOT_DB_URL, db_read_only, resolve_table_mapping = _load_db_api()
    except ModuleNotFoundError as exc:
        print("❌ Не хватает Python-зависимостей для запуска init_db.")
        print(f"Причина: {exc}")
        print("Установите зависимости текущим интерпретатором:")
        print("python3 -m pip install -r requirements.txt")
        return 1

    print(f"Используем БД: {_safe_db_url(BOT_DB_URL)}")
    print(f"Режим БД: {'read-only' if db_read_only else 'read-write'}")

    try:
        table_map = resolve_table_mapping()
        print("✅ Найдены таблицы FriendlyMap:")
        print(f"- users: {table_map['users']}")
        print(f"- achievements: {table_map['achievements']}")
        print(f"- user_achievements: {table_map['user_achievements']}")
        return 0

    except RuntimeError as exc:
        print(f"❌ {exc}")
        return 1
    except Exception as exc:
        _print_connection_help(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
