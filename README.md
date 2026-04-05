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

## Отображение рангов на сайте
- Сайт показывает только `Ранг` и `GP`, без `Общий GP` и без `GP в ранге`.
- Для рангов 1–9 UI показывает `GP: X/100`.
- Для `🟣 Картограф` UI показывает `GP: X/400`, где `X = min(total_gp - 900, 400)`.
- Для `⭐ Мастер-картограф` UI показывает `GP: 400/400` при `total_gp = 1300` и `GP: 400+/400` при `total_gp > 1300`.

## Runtime: какие VIEW использует сайт
- `/leaderboard` → `site_leaderboard`
- `/profile/{user_id}` → `site_public_users`
- `/profile/me` → protected профиль текущего пользователя
- `/achievements` → `site_achievements_overview`
- `/add-location` → web add-location flow
- `/map` → карта подтверждённых локаций

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
4. Проверить auth, add-location и map:
   - `/login` поддерживает email и Telegram WebApp login
   - `/api/session/me` возвращает состояние web-сессии (`authenticated`, `user_id`)
   - `/profile/me` требует сессию
   - `/add-location` рендерится
   - `/api/add-location/form-config`, `/api/add-location/upload`, `/api/add-location/preview`, `/api/add-location/submit` доступны и защищены cookie-сессией
   - при `DB_READ_ONLY=1` submit блокируется с понятной ошибкой
   - `/map` показывает точки, поиск и фильтры по тегам, кнопку геопозиции и аккуратный control-panel UI

## Add-location flow
В этом репозитории реализован полноценный web flow добавления локации:

- UI-страница: `/add-location`
- API:
  - `GET /api/add-location/form-config`
  - `POST /api/add-location/upload`
  - `POST /api/add-location/preview`
  - `POST /api/add-location/submit`
  - `GET /api/session/me` (состояние текущей web-сессии)
  - `GET /api/map/locations` + `GET /api/map/tags` (поиск/фильтр карты)

### Что реализовано
- Пошаговый UX (name/description/coordinates/tags/photos/preview/submit).
- Выбор координат через карту (Leaflet) с marker selection как основной UX (ручной ввод скрыт как fallback).
- На add-location и /map есть кнопка определения геопозиции пользователя.
- Client-side + server-side валидация обязательных полей.
- Реальная запись pending-локации в write-режиме (`DB_READ_ONLY=0`).
- Атомарный submit path с idempotency key.
- Upload и хранение web-фото в `MEDIA_ROOT` + обратная совместимость legacy `file_id`.
- Каталог тегов берётся из БД (`tags`) и seed-ится полным каталогом.
- Полный bot tag catalog синхронизируется idempotent-миграцией в `tags` (slug/code/name/category).
- Есть `/map` + `/api/map/locations` для просмотра approved locations.
- На `/map` есть поиск по названию/описанию и фильтр по тегу.
- Список тегов для карты грузится из БД (`tags`) через `GET /api/map/tags` и совпадает с add-location catalog (`/api/add-location/form-config`).
- Категории тегов отображаются и в add-location (чипы), и в map filter (grouped select).
- Есть login/logout и session-cookie, `/add-location` и write API защищены.
- `POST /api/session/email` и `POST /api/session/telegram` поддерживают `next` и устанавливают signed cookie `fm_session`.

### Runtime требования для submit
- `DB_READ_ONLY=0`
- `TELEGRAM_BOT_TOKEN` задан (для проверки `X-Telegram-Init-Data`)
- `SECRET_KEY` задан (подпись session-cookie)
- write-права к таблицам `users`, `locations`, `tags`, `location_tags`, `photos`
- `MEDIA_ROOT` доступен на запись

### Auth / session env vars
- `SECRET_KEY` — обязателен для подписи web cookie-сессий.
- `SESSION_TTL_SECONDS` — TTL cookie-сессии (по умолчанию 86400 секунд).
- `SESSION_COOKIE_SECURE=1` — включить secure-cookie за reverse proxy + HTTPS.

### Media и миграции
- На старте в write-режиме вызывается `ensure_add_location_schema()`:
  - добавляются дополнительные колонки в `photos` (если отсутствуют),
  - создаётся `site_submission_idempotency`,
  - создаётся/синхронизируется таблица `tags` (slug/code/name/category),
  - выполняется idempotent upsert полного bot tag catalog.
