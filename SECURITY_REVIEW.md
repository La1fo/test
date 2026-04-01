# Security review (FriendlyMap Site Reader)

## Scope checked
- Backend Python code in `backend/`.
- Configuration in `.env` and dependency pins in `requirements.txt`.
- Frontend templates in `frontend/`.

## Key security decisions
1. **Strict DB read-only architecture**
   - Site is designed as reader-only service over shared FriendlyMap DB.
   - Primary integration path is explicit SQL VIEW contract (`site_*`), not direct writes.

2. **No schema guessing in primary mode**
   - Main mode validates explicit DB contract and fails fast if missing/incompatible.
   - Legacy schema guessing exists only behind `LEGACY_SCHEMA_COMPAT=1`.

3. **Auth secret and token hardening**
   - `SECRET_KEY` must be at least 32 chars.
   - Token signing and password verification use constant-time comparisons.

4. **Telegram auth validation hardening**
   - Payload signature validated with HMAC.
   - `auth_date` freshness check blocks replay attempts.

## Contract and startup safety
- Startup contract check validates required `site_*` VIEW and required columns.
- On contract mismatch, service returns explicit diagnostics rather than silent fallbacks.

## Additional recommendations
- Keep DB role minimal (`SELECT` only on contract VIEW).
- Add CI checks for tests + security linting.
- Keep production secrets in secret manager, not in repository.
