# TASK-01 Auth Fixes

- `backend/src/api/routes/auth.py`
  - Added CAPTCHA enforcement to `reset_password`.
  - Added CAPTCHA enforcement to `resend_verification`.
  - Added reset context hashing from IP and user-agent.
  - Stores reset token context as durable DB records and rejects mismatched reset attempts.
  - Persists only SHA-256 reset token hashes; raw reset tokens are never stored.
  - Marks auth-sensitive rate-limit dependencies as fail-closed capable.

- `backend/src/models/user.py` / `backend/alembic/versions/028_add_password_reset_tokens.py`
  - Added `PasswordResetToken` / `password_reset_tokens`.
  - Indexed token hash, user active tokens, and expiry for lookup and cleanup.
  - Consumes prior active reset tokens when issuing a new one.

- `backend/src/core/config.py`
  - Added `AUTH_REDIS_FAIL_CLOSED` for explicit fail-closed rehearsal outside staging/production.

- `backend/src/core/security.py` / `backend/src/core/deps.py`
  - Added `RateLimitBackendUnavailable`.
  - Redis-backed auth rate limits now return `503` with `Retry-After` when fail-closed is active and Redis is unavailable.

- `frontend/src/lib/api.ts`
  - `resetPassword` accepts optional `captcha_token`.
  - `resendVerification` accepts optional `captcha_token`.
  - All shared request/refresh paths use `credentials: include` and refresh via HttpOnly cookie or one-time legacy refresh-token body.
  - Removed remaining production `localStorage.getItem('access_token')` reads from API helper surfaces.

- `frontend/src/lib/platform/storage.ts` / `frontend/src/lib/store.ts`
  - Browser access token is memory-backed only.
  - Browser refresh token is no longer persisted by JS; legacy `refresh_token` is consumed once for silent migration.
  - Legacy `access_token`, `refresh_token`, and `auth-storage.state.token` are removed/sanitized during storage access.
  - Desktop Tauri store remains the non-browser persistence path and no longer mirrors tokens into browser localStorage.

- `frontend/src/App.tsx` / auth consumers
  - Added startup auth bootstrap: restore memory token from storage, then silent-refresh via cookie/legacy body, then fetch `/auth/me` if needed.
  - `ProtectedRoute`, `AdminRoute`, IM/collaboration/admin/payment/template surfaces now read token from memory storage instead of localStorage.

- `frontend/src/pages/Login.tsx`
  - Reset-password step accepts a high-entropy reset token instead of a 6-digit code.
- Reset-password and resend-verification submit CAPTCHA token when required.
- Auto resend after unverified login is skipped when CAPTCHA is required.

- `backend/.env.example`
  - Documents `AUTH_REDIS_FAIL_CLOSED=true` for deployable environments.
