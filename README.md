# Friendly Map Website

## Запуск (PostgreSQL)

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
2. Поднимите PostgreSQL и создайте БД `friendly_map`.
3. Создайте `.env` на основе `.env.example`.
4. Обязательно заполните:
   - `DATABASE_URL` (валидный URL для PostgreSQL с корректными логином/паролем)
   - `SECRET_KEY` (минимум 32 символа)
5. Инициализируйте БД:
   ```bash
   python -m backend.init_db
   ```
6. Запустите сервер:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
   ```

## Важное по безопасности

- Приложение работает **только** с PostgreSQL.
- При отсутствии `DATABASE_URL` приложение завершится с понятной ошибкой (fail-fast).
- Telegram auth проверяется с TTL (`TELEGRAM_AUTH_MAX_AGE_SECONDS`) для защиты от replay-атак.
- Подпись Telegram проверяется через `hmac.compare_digest`.
- Access token подписывается HS256 и содержит `iat`/`exp`.
- Для паролей используется `bcrypt`.
