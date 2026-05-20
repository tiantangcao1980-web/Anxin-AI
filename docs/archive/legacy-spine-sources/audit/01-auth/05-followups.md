# TASK-01 Auth Followups

1. Token storage migration:
   - Add an E2E that logs in through the real UI and asserts `localStorage.getItem('access_token') === null`.
   - Audit mobile/desktop refresh behavior before deciding whether any deployment must temporarily set `AUTH_REFRESH_BODY_COMPAT_ENABLED=true`.
   - Review mobile and desktop token policies separately; Web source is now localStorage-free for auth tokens.

2. Redis fail-closed:
   - Audit any remaining Redis-backed session table or CAPTCHA state surfaces outside rate limiting and refresh blacklist.
   - Run staging chaos verification that kills Redis during auth flows.

3. Durable reset token storage:
   - Add scheduled cleanup for expired/consumed `password_reset_tokens` records.
   - Add operational metric/alerting for abnormal reset-token issue and consume rates.

4. Frontend CAPTCHA coverage:
   - Add CAPTCHA UX for Settings email resend or hide/route it through the verified auth flow when CAPTCHA is enabled.
