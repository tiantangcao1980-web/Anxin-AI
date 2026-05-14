# TASK-01 Auth Issues

## Closed

- Reset-password checked token validity before CAPTCHA, letting automated probes distinguish invalid-token behavior without solving CAPTCHA.
- Resend-verification did not require CAPTCHA.
- Reset-password UI constrained the high-entropy reset token input to six characters.
- Reset token was not bound to request context.
- Auth-sensitive rate limiting fell back to local memory when Redis was unavailable.
- Refresh-token blacklist fail-closed behavior existed but had no regression test.

## Open

- localStorage token footprint remains broad and is the next auth P0.
- Mobile/desktop refresh behavior still needs audit before any deployment temporarily re-enables body refresh via `AUTH_REFRESH_BODY_COMPAT_ENABLED=true`.
