# TASK-01 Auth PRD Coverage

| Item | Status | Evidence |
|---|---|---|
| P0-1 high-entropy reset token | Closed for backend | Token is high entropy, 15-minute, single-use, IP/UA bound, and persisted as SHA-256 hash records in `password_reset_tokens` via Alembic `028_password_reset_tokens`. |
| P0-2 no production token in localStorage | Closed for Web | `frontend/src` no longer reads/writes `access_token`, `refresh_token`, `auth_token`, or `auth-storage` token fields in localStorage. Browser storage keeps access token in memory, uses HttpOnly refresh cookie, and consumes legacy localStorage refresh once during migration. |
| P0-3 Redis auth fail-closed | Partial | Auth-sensitive rate limits return 503 when fail-closed is enabled or in staging/production; refresh-token blacklist fail-closed is covered. Durable session-table Redis checks still need audit. |
| P0-4 CAPTCHA full coverage | Partial | reset-password and resend-verification are now covered; any additional SMS/email resend surfaces still need audit. |
| P0-5 single source of auth truth | Closed for Web | Zustand no longer persists token; `TokenStorage` owns access-token memory state and legacy cleanup. |
