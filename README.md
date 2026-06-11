# FriendlyMap Site

Сайт работает как самостоятельный веб-сервис FriendlyMap: пользователи регистрируются по email, входят через cookie-сессию, смотрят карту подтверждённых локаций и отправляют новые точки на модерацию. По умолчанию сайт работает в write-mode и сам создаёт/обновляет нужные таблицы, индексы, справочники и `site_*` VIEW при запуске.

## Обязательный DB contract (VIEW)
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
   - `telegram_id` (legacy nullable column; не нужен для веб-регистрации)
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
   - `telegram_id` (legacy nullable column)
   - `email`
   - `hashed_password` (`users.password_hash`)

## Каноническая ранговая система
Источник истины — `total_gp`.

Формула:
- `rank_level = floor(total_gp / 100) + 1`
- `gp_in_rank = total_gp % 100`
- `rank_name = "Ранг {rank_level}"`

## Роль БД
Для read-only режима достаточно роли `friendly_site_ro`:
- `CONNECT` к БД
- `USAGE` на `public`
- `SELECT` на `site_*` VIEW

Для write-mode рекомендуется отдельная роль `friendly_site_rw`:
- `SELECT` на `site_*` VIEW
- `INSERT/UPDATE` на `users`, `locations`, `photos`, `tags`, `location_tags`, `site_submission_idempotency`
- права на соответствующие sequence (`USAGE`, `SELECT`, при необходимости `UPDATE`)

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
4. Инициализировать/проверить БД:
   ```bash
   python3 -m backend.init_db
   ```
   При `DB_BOOTSTRAP_SCHEMA=1` команда создаст/обновит таблицы сайта, заполнит каталог тегов и пересоздаст контрактные `site_*` VIEW, затем проверит контракт. Для полностью read-only окружения установите `DB_BOOTSTRAP_SCHEMA=0` и заранее подготовьте контрактные VIEW.
5. Запустить сайт:
   ```bash
   python3 -m backend.main
   ```

## Runtime: какие VIEW использует сайт
- `/leaderboard` → `site_leaderboard`
- `/profile/{user_id}` → `site_public_users`
- `/profile/me` → protected профиль текущего пользователя
- `/achievements` → `site_achievements_overview`
- `/add-location` → web add-location flow
- `/map` → карта подтверждённых локаций
- `/login` → email login + email registration
- `/logout` → выход из cookie-сессии

## Auth и session
- `POST /api/session/register` создаёт запись в `users` (`email`, `password_hash`, профильные defaults) и сразу ставит signed cookie `fm_session`.
- `POST /api/session/email` логинит по `site_auth_users.email` + `hashed_password`.
- `GET /api/session/me` возвращает `{ authenticated, user_id }`.
- Navbar единый на всех страницах: guest видит `Войти`, auth user видит `Мой профиль`; `Выйти` доступен на странице профиля.

## Add-location flow
- UI-страница: `/add-location`
- API:
  - `GET /api/add-location/form-config`
  - `POST /api/add-location/upload`
  - `POST /api/add-location/preview`
  - `POST /api/add-location/submit`
  - `GET /api/map/locations`
  - `GET /api/map/tags`

### Что реализовано
- Пошаговый UX (name/description/coordinates/tags/photos/preview/submit).
- Выбор координат через Leaflet marker selection; ручной ввод скрыт как fallback.
- Geolocation на `/add-location` и `/map`.
- Client-side + server-side валидация обязательных полей.
- Реальная запись pending-локации в write-mode (`DB_READ_ONLY=0`).
- Атомарный submit path с idempotency key, привязанным к `user_id` текущей веб-сессии.
- Upload и хранение web-фото в `MEDIA_ROOT`.
- Каталог тегов берётся из БД (`tags`) и seed-ится полным каталогом FriendlyMap.
- `/add-location` для гостя показывает auth-required CTA; `/map` для гостя доступна для просмотра и показывает login CTA.

## Runtime требования для write-mode
- `DB_READ_ONLY=0` — включает регистрацию и отправку локаций (значение по умолчанию).
- `DB_BOOTSTRAP_SCHEMA=1` — создаёт/обновляет таблицы и `site_*` VIEW при запуске и в `python3 -m backend.init_db` (значение по умолчанию).
- `SECRET_KEY` задан (подпись session-cookie)
- `MEDIA_ROOT` доступен на запись
- write-права к `users`, `locations`, `photos`, `tags`, `location_tags`, `achievements`, `user_achievements`, `site_submission_idempotency` и права на соответствующие sequence

### Auth / session env vars
- `SECRET_KEY` — обязателен для подписи web cookie-сессий.
- `SESSION_TTL_SECONDS` — TTL cookie-сессии (по умолчанию 86400 секунд).
- `SESSION_COOKIE_SECURE=1` — включить secure-cookie за reverse proxy + HTTPS.

## Миграции
Если `DB_BOOTSTRAP_SCHEMA=1`, на старте вызывается `ensure_site_schema()` до проверки DB contract:
- `ensure_core_schema()` создаёт базовые таблицы сайта: `users`, `locations`, `photos`, `tags`, `location_tags`, `achievements`, `user_achievements`; для частично существующих таблиц добавляет недостающие колонки и индексы.
- `ensure_add_location_schema()` добавляет web-photo колонки в `photos`, создаёт `site_submission_idempotency`, создаёт/синхронизирует `tags` и полный FriendlyMap tag catalog.
- `ensure_auth_schema()` добавляет auth/profile поля в `users` (`email`, `password_hash`, `email_verified`, и др.) и создаёт уникальный индекс `LOWER(email)`.
- `ensure_contract_views()` создаёт/обновляет все контрактные `site_*` VIEW: `site_public_users`, `site_leaderboard`, `site_public_locations`, `site_achievements_overview`, `site_auth_users`.

После миграций приложение всегда запускает проверку DB contract, поэтому если VIEW не соответствуют ожиданиям, сайт останавливается с понятной ошибкой.

При `DB_READ_ONLY=1` registration и add-location upload/submit отключаются, но при `DB_BOOTSTRAP_SCHEMA=1` приложение всё равно попытается подготовить схему перед проверкой контракта. Для роли без write-прав установите `DB_BOOTSTRAP_SCHEMA=0`; тогда публичные reader routes и карта будут доступны только при заранее созданных `site_*` VIEW.
