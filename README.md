# FriendlyMap

## Безопасный запуск с PostgreSQL

1. Создайте и активируйте виртуальное окружение (рекомендуется):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Установите зависимости **тем же интерпретатором**, которым будете запускать проект:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
3. Заполните `.env`:
   - `SECRET_KEY` (минимум 32 случайных символа)
   - `DATABASE_URL`, либо `POSTGRES_HOST/PORT/DB/USER/PASSWORD`
4. Инициализируйте БД:
   ```bash
   python3 -m backend.init_db
   ```
5. Запустите сайт:
   ```bash
   python3 -m backend.main
   ```

## Безопасность
- Отчёт по проверке безопасности: `SECURITY_REVIEW.md`.
- Не храните реальные секреты в git; используйте переменные окружения/секрет-хранилище.


### Режим только чтения
- По умолчанию `DB_READ_ONLY=1`: приложение ожидает, что таблицы уже существуют в БД из основного проекта FriendlyMap.
- В этом режиме `init_db` только проверяет доступность и имена уже существующих таблиц.
- Таблицы должны быть предварительно созданы основным проектом FriendlyMap.

- Если в уже созданной БД таблицы называются иначе, задайте: `FM_USERS_TABLE`, `FM_ACHIEVEMENTS_TABLE`, `FM_USER_ACHIEVEMENTS_TABLE`.
