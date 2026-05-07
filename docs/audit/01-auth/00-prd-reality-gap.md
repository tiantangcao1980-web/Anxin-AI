# TASK-01 Auth Reality Gap

> Date: 2026-05-06
> Scope: authentication, password reset, CAPTCHA coverage, frontend auth calls.

## Confirmed

- Login/register/forgot-password already call CAPTCHA when Turnstile is enabled.
- Password reset token generation already uses a high-entropy URL-safe token and 15-minute expiry.
- Refresh token is set as an HttpOnly cookie on login/refresh.
- Web access token storage is now memory-backed; production `frontend/src` no longer reads or writes `access_token` / `refresh_token` / `auth_token` in localStorage.

## Closed In This Pass

- Reset-password submission now requires CAPTCHA when CAPTCHA is enabled.
- Resend-verification now requires CAPTCHA when CAPTCHA is enabled.
- Password reset token is bound to request IP hash and user-agent hash.
- Password reset token remains single-use after successful reset.
- Password reset token storage is now durable: raw tokens are never persisted, only SHA-256 hashes in `password_reset_tokens`.
- Auth-sensitive rate limiting can fail closed with `503` + `Retry-After` when Redis is unavailable; staging/production enable this automatically, and development/test can opt in with `AUTH_REDIS_FAIL_CLOSED=true`.
- Refresh token rotation already fails closed when blacklist Redis is unavailable, and now has explicit regression coverage.
- Frontend reset-password and resend-verification calls now pass `captcha_token`.
- Reset-password UI no longer assumes a 6-digit code; it accepts a high-entropy reset token.

## Still Blocking Commercial Delivery

- Backend refresh request-body compatibility now has an explicit sunset switch: disabled by default and only re-enabled with `AUTH_REFRESH_BODY_COMPAT_ENABLED=true`.
- Settings email resend has no dedicated CAPTCHA UX; backend now correctly rejects it when CAPTCHA is enabled.
- Cookie refresh remains the default; body refresh is now an explicit temporary migration switch.
