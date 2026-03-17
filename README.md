# FriendlyMap Site (Reader Service)

Сайт работает как **read-only сервис** поверх общей БД FriendlyMap.
Writer-логика (бот/бэкенд) пишет данные, сайт только читает.

## DB contract (обязательный)
Сайт ожидает следующие `VIEW` в схеме `public`:

- `site_leaderboard`
  - `user_id`, `username`, `gp_points`, `rank_name`
- `site_public_users`
  - `user_id`, `username`, `telegram_id`, `email`, `hashed_password`
- `site_public_locations`
  - `location_id`, `user_id`
- `site_achievements_overview`
  - `achievement_id`, `name`, `description`, `reward_points`, `is_seasonal`

> Рекомендуется поддерживать эти VIEW в writer-проекте, чтобы сайт не зависел от внутренних таблиц бота.

## Роль БД
Используйте отдельную роль только для чтения, например `friendly_site_ro`:
- `CONNECT` к БД
- `USAGE` на схему `public`
- `SELECT` только на `site_*` VIEW

## Запуск
1. Создайте venv:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Установите зависимости:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
3. Заполните `.env`.
4. Проверьте контракт:
   ```bash
   python3 -m backend.init_db
   ```
5. Запустите сайт:
   ```bash
   python3 -m backend.main
   ```

## Legacy compatibility
По умолчанию **выключено**.

- `LEGACY_SCHEMA_COMPAT=0` — строгий контракт через `site_*` VIEW (рекомендуется)
- `LEGACY_SCHEMA_COMPAT=1` — временный fallback угадывания схемы (только для миграции)

## Безопасность
- `SECRET_KEY` должен быть минимум 32 символа.
- Не храните реальные секреты в git.
- Сайт не должен выполнять write-операции в бизнес-таблицы FriendlyMap.
