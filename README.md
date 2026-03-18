# FriendlyMap Site (Reader Service)

Сайт работает как **reader-only** сервис поверх общей БД FriendlyMap.
Бот/основной backend — единственные writer-сервисы.

## Обязательный DB contract (read-only VIEW)
Сайт ожидает в `public` следующие VIEW:

1. `site_leaderboard`
   - `user_id`
   - `username`
   - `total_gp`
   - `rank_level`
   - `gp_in_rank`
   - `rank_name`
   - `position`

2. `site_public_users`
   - `user_id`
   - `username`
   - `telegram_id`
   - `total_gp`
   - `rank_level`
   - `gp_in_rank`
   - `rank_name`
   - `approved_locations`

3. `site_public_locations`
   - `location_id`
   - `user_id`

4. `site_achievements_overview`
   - `achievement_id`
   - `code`
   - `name`
   - `description`
   - `completed_count`
   - `is_seasonal`

5. `site_auth_users`
   - `user_id`
   - `username`
   - `telegram_id`
   - `email`
   - `hashed_password`

## Каноническая ранговая система
Источник истины — `total_gp`.

Формула:
- `rank_level = floor(total_gp / 100) + 1`
- `gp_in_rank = total_gp % 100`
- `rank_name = "Ранг {rank_level}"`

Пример:
- `total_gp=99` → `Ранг 1`, `99 GP`
- `total_gp=102` → `Ранг 2`, `2 GP`

## Роль БД (минимальные права)
Рекомендуемая роль сайта: `friendly_site_ro`
- `CONNECT` к БД
- `USAGE` на `public`
- `SELECT` только на `site_*` VIEW

## Запуск
1. Создать venv:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Установить зависимости:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
3. Заполнить `.env`.
4. Проверить контракт:
   ```bash
   python3 -m backend.init_db
   ```
5. Запустить сайт:
   ```bash
   python3 -m backend.main
   ```

## Legacy compatibility
По умолчанию отключён:
- `LEGACY_SCHEMA_COMPAT=0` — строгий контрактный режим
- `LEGACY_SCHEMA_COMPAT=1` — временный fallback legacy-маппинга (только миграция)

## Ограничения read-only режима
- Сайт не пишет в shared бизнес-данные.
- Email registration на reader-сервисе отключена.
- Telegram/email login только чтение через `site_auth_users`.

## Runtime: какие VIEW использует сайт
- `/leaderboard` → `site_leaderboard`
- `/profile/{user_id}` → `site_public_users`
- `/achievements` → `site_achievements_overview`
- `/auth/telegram` → `site_auth_users`
- `/auth/email/login` → `site_auth_users`
- `/auth/email/register` → отключён на reader-side (`403`)

## Startup diagnostics
- `python3 -m backend.init_db` печатает режим схемы (`strict-contract`/`legacy-compat`) и ожидаемые VIEW.
- При ошибке контракта выводится конкретная диагностика: отсутствующая VIEW и/или список недостающих колонок.

## Release verification steps
1. Проверить контракт и диагностику старта:
   ```bash
   python3 -m backend.init_db
   ```
2. Запустить unit-тесты (contract/auth/runtime/rank):
   ```bash
   python3 -m unittest discover -s tests -v
   ```
3. Запустить сайт и открыть ключевые страницы:
   - `/leaderboard`
   - `/profile/{user_id}`
   - `/achievements`
4. Проверить auth reader-flow:
   - `/auth/telegram` и `/auth/email/login` читают только `site_auth_users`
   - `/auth/email/register` возвращает `403`
