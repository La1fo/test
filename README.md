# Friendly Map Website

## Запуск (PostgreSQL)

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
2. Убедитесь, что PostgreSQL запущен и создана БД `friendly_map`.
3. Создайте `.env` на основе `.env.example` и заполните `SECRET_KEY` (минимум 32 символа).
4. Инициализируйте БД:
   ```bash
   python -m backend.init_db
   ```
5. Запустите сервер:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
   ```

## Переменные окружения

- `DATABASE_URL` — **обязательно PostgreSQL** (`postgresql://...` или `postgresql+psycopg2://...`).
- `SECRET_KEY` — секрет подписи токенов (минимум 32 символа).
- `ACCESS_TOKEN_EXPIRE_MINUTES` — время жизни access token.
- `TELEGRAM_AUTH_MAX_AGE_SECONDS` — TTL Telegram auth payload (защита от replay-атак).
- `TELEGRAM_BOT_TOKEN` — токен Telegram-бота для auth.
- `TELEGRAM_BOT_USERNAME` — username бота для шаблонов.

## Что исправлено по безопасности

- Убраны hardcoded креды внешней БД.
- Добавлена строгая проверка, что приложение использует PostgreSQL.
- Токен теперь формируется в формате JWT (HS256, `header.payload.signature`) с `iat`/`exp`.
- Включена проверка `auth_date` Telegram с TTL для защиты от replay.
- Используется `hmac.compare_digest` для безопасного сравнения подписи.
- Добавлены security headers (`CSP`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`).
- Добавлен rollback/обработка `IntegrityError`, чтобы избежать неконсистентных транзакций.
