# FriendlyMap

## Запуск с PostgreSQL
1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
2. Заполните `.env`:
   - `SECRET_KEY` (минимум 32 символа)
   - либо `DATABASE_URL`, либо `POSTGRES_HOST/PORT/DB/USER/PASSWORD`
3. Инициализируйте БД:
   ```bash
   python -m backend.init_db
   ```
4. Запустите сайт:
   ```bash
   python -m backend.main
   ```

Подробный отчет по безопасности: `SECURITY_REVIEW.md`.
