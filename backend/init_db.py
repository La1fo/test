"""Проверка готовности read-only DB contract для сайта FriendlyMap."""

from urllib.parse import urlsplit


def _safe_db_url(db_url: str) -> str:
    parts = urlsplit(db_url)
    if not parts.password:
        return db_url

    host = parts.hostname or "localhost"
    port = f":{parts.port}" if parts.port else ""
    user = parts.username or "user"
    return f"{parts.scheme}://{user}:***@{host}{port}{parts.path}"


def main() -> int:
    try:
        from .database import BOT_DB_URL, DB_READ_ONLY, LEGACY_SCHEMA_COMPAT, get_db_contract, validate_db_contract
    except ModuleNotFoundError as exc:
        print("❌ Не хватает Python-зависимостей для запуска init_db.")
        print(f"Причина: {exc}")
        print("Установите зависимости текущим интерпретатором:")
        print("python3 -m pip install -r requirements.txt")
        return 1

    contract = get_db_contract()
    print(f"Используем БД: {_safe_db_url(BOT_DB_URL)}")
    print(f"Режим БД: {'read-only' if DB_READ_ONLY else 'read-write'}")
    print(f"Legacy compatibility: {'on' if LEGACY_SCHEMA_COMPAT else 'off'}")
    print("Ожидаемые VIEW контракта:")
    print(f"- leaderboard: {contract.leaderboard_view}")
    print(f"- public_users: {contract.public_users_view}")
    print(f"- public_locations: {contract.public_locations_view}")
    print(f"- achievements: {contract.achievements_view}")
    print(f"- auth_users: {contract.auth_users_view}")

    try:
        ok, errors = validate_db_contract()
        if ok:
            print("✅ DB contract валиден")
            return 0

        print("❌ DB contract невалиден:")
        for err in errors:
            print(f"  - {err}")
        return 1
    except Exception as exc:
        print("❌ Не удалось проверить DB contract.")
        print(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
