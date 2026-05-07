# TASK-01 Auth Test Additions

Added to `backend/tests/test_auth_surface_hardening.py`:

- `test_reset_password_requires_captcha_when_enabled`
- `test_resend_verification_requires_captcha_when_enabled`
- `test_password_reset_token_is_high_entropy_single_use_and_context_bound`
- `test_auth_rate_limit_fails_closed_when_redis_down`
- `test_forgot_password_rate_limit_fails_closed_when_redis_down`
- `test_refresh_token_blacklist_fails_closed_when_redis_down`
- `test_refresh_endpoint_rejects_body_token_after_compat_sunset`
- `test_refresh_endpoint_still_accepts_cookie_when_body_compat_disabled`
- `test_refresh_endpoint_accepts_cookie_without_request_body`

Verification:

```bash
cd backend && ./.venv/bin/pytest -q tests/test_auth_surface_hardening.py
# 16 passed

cd backend && ./.venv/bin/ruff check alembic/versions/028_add_password_reset_tokens.py tests/test_auth_surface_hardening.py
# All checks passed

cd backend && ./.venv/bin/pytest -q tests/test_deployment_migrations.py
# 2 passed

cd backend && ./.venv/bin/pytest -q tests/test_im_websocket_auth.py
# 2 passed

cd backend && ./.venv/bin/pytest -q tests/test_realtime_authorization_guards.py tests/test_im_websocket_auth.py
# 4 passed

cd backend && ./.venv/bin/pytest -q
# 354 passed, 1 skipped, 3 warnings in 43.66s

cd frontend && npm run lint
# exit 0

cd frontend && npm test
# 8 passed

cd frontend && npm test -- api.test.ts
# 3 passed

cd frontend && npm run build
# exit 0

cd frontend && npx playwright test e2e/role-access.spec.ts
# 10 passed, 10 skipped
```
