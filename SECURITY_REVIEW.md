# Security review (FriendlyMap)

## Scope checked
- Backend Python code in `backend/`.
- Configuration in `.env` and dependency pins in `requirements.txt`.
- Frontend static templates in `frontend/`.

## High-risk issues found and fixed
1. **Unsafe/default JWT secret usage**
   - Risk: predictable default key allows token forgery.
   - Fix: `backend/security.py` now requires `SECRET_KEY` of at least 32 chars and fails fast if not configured.

2. **Telegram auth signature verification weaknesses**
   - Risk: replay attacks and timing attacks in hash compare.
   - Fix: `verify_telegram_auth` now:
     - validates payload as dict,
     - enforces `auth_date` freshness (10 minutes),
     - uses `hmac.compare_digest` for constant-time comparison,
     - avoids mutating input payload.

3. **Broken auth endpoint models / runtime errors**
   - Risk: auth endpoints could fail unexpectedly (undefined variables and wrong model import), potentially exposing stack traces.
   - Fix: corrected payload handling in `backend/api/auth.py`, replaced unknown `User` with `WebsiteUser`, and added typed Telegram payload schema.

4. **Weak input validation for registration**
   - Risk: invalid email / overly short passwords accepted.
   - Fix: `backend/schemas.py` now validates email via `EmailStr` and enforces sensible bounds for username/password.

5. **Database auth misconfiguration visibility**
   - Risk: startup/init failures with unclear troubleshooting.
   - Fix: `backend/init_db.py` now prints sanitized DB URL and human-readable PostgreSQL diagnostics for common failures.

## PostgreSQL readiness
- Database URL resolution now prioritizes `DATABASE_URL`/`DB_URL`, otherwise builds PostgreSQL DSN from `POSTGRES_*` variables.
- SQLAlchemy engine uses `pool_pre_ping` and `pool_recycle` to reduce stale-connection errors.

## Additional recommendations (not auto-fixed)
- Add rate limiting for `/email/login` and `/telegram` endpoints to mitigate brute-force attacks.
- Add account lockout/backoff policy on repeated failed logins.
- Add HTTPS-only cookie session strategy if browser auth is used.
- Add CI security checks (`pip-audit`, `bandit`, and SAST) and dependency update workflow.
- Do not commit real secrets into `.env` in production; use environment/secret manager.
