# Security checklist review — 2026-09-28

Scope: owner-supplied 20-item checklist against current FastAPI/SQLite application.
Reviewed code and isolated tests, never live records, credentials or secret files.
This is an engineering review, not a penetration test or production certification.

| # | Checklist item | Current finding / decision |
|---|---|---|
| 1 | Hide API keys | No browser-side database/API key architecture. Session signing material is server-side; production now requires an external secret and never falls back to the local secret file. No actual secrets opened. |
| 2 | Purge Git secrets | Ignore rules cover env/secret/database files. Current index and all-ref filename history found none of those protected names. A limited common-key-pattern scan of tracked app/scripts found no matches. This is not an exhaustive historical content scan; no history was rewritten and no credentials rotated. |
| 3 | Use public DB key | Not applicable: the browser never connects directly to SQLite; adding a public database key would not help. |
| 4 | Row-level security | SQLite has no equivalent hosted-DB RLS layer here. Server role, active-enrollment and ownership checks enforce access; other students' attempts are denied. Teachers intentionally manage the shared course; no invented multi-tenant isolation claim. |
| 5 | Encrypt sensitive data | Passwords are hashed. SQLite and backup contents are not application-encrypted. Disk encryption/protected backup storage is an unresolved operational requirement; host encryption was not inspected or changed. Custom field encryption without key/recovery management is deferred. |
| 6 | Server-side authentication | Existing revocable database sessions; expired/reset/deleted credentials rejected. Mutation services reauthorize under the write lock. |
| 7 | Lock record access | Role/student ownership checks, FK/uniqueness constraints and immutable history triggers; permanent lesson completion. Existing regression coverage. |
| 8 | Block field tampering | Explicit accepted form fields, server-derived identity/correctness, CSRF, revision/version checks. Client values never assign teacher privileges. |
| 9 | Secure session cookies | Existing HttpOnly/SameSite=Lax. Added production Secure flag; local HTTP remains usable. Cookies are signed, not encrypted, and contain opaque session reference/CSRF rather than passwords or student records. |
| 10 | Hash passwords | Existing Argon2 via pwdlib recommended hasher; no reversible password storage. |
| 11 | Rate-limit login | Existing account/IP limits persist in SQLite and handle classroom shared-IP behavior. Attendance-code attempts also limited. |
| 12 | Bot protection | Existing rate limits, CSRF, teacher-issued accounts and bounded uploads are appropriate baseline for pilot. CAPTCHA/WAF deferred until public-host needs or observed abuse justify student friction. Not claiming general bot/DDoS protection. |
| 13 | Parameterize queries | SQLAlchemy bound values for request data. Dynamic backup/schema SQL uses internal table names; no request values concatenated into those statements. |
| 14 | Validate input | Existing lengths, IDs, enums, foreign relationships, status transitions and bounded request sizes. Added generic 422 handling that does not echo raw submitted values. |
| 15 | Escape user content | Jinja autoescaping; highlighting uses textContent/text nodes, no user HTML insertion. Existing escaping tests. |
| 16 | Restrict file uploads | Teacher-only, CSRF, one-file/10 MB/100-page PDF profile bounds, private temporary parsing, timeout, review gate and no serving original uploads. Parser isolation is not an OS sandbox/hard RAM quota. No feature expansion here. |
| 17 | Trim API responses | Existing explicit practice projection hides answers until submission and enforces attempt ownership. Added raw validation-input suppression and disabled docs/OpenAPI in production. |
| 18 | Security headers | Existing CSP, nosniff, same-origin referrer policy, no-store for non-static responses. New production-only HSTS on HTTPS. |
| 19 | Force HTTPS | Added production redirect and explicit trusted hosts; invalid hosts rejected before redirect. Real TLS certificate, proxy configuration and actual deployment remain pending. |
| 20 | Scan dependencies | Latest 2026-09-28 PyPI version advisory metadata checked 30 pins, no listed advisories/unavailable packages; docs/dependency-audit.json. No dependency change in this slice. Advisory absence is not proof of vulnerability absence. |

## Production configuration prepared, not activated

`SAT_FACTORY_ENV=production` enables secure cookies, HTTPS redirect, trusted hosts,
HSTS and disabled docs/OpenAPI. Startup fails without:
- `SAT_FACTORY_SESSION_SECRET`: an externally supplied randomly generated secret,
  at least 64 characters. Set via the host's secret manager/environment; never commit.
- `SAT_FACTORY_ALLOWED_HOSTS`: comma-separated exact hostnames, no scheme, port or
  wildcard. Use the eventual approved address, not a fabricated public hostname.

Default `development` continues existing local HTTP. Unknown environment names fail
closed. Tests use explicitly fictional injected settings, not real environment secrets.

Before activation, TLS must terminate at an approved proxy. Bind the application
privately and trust forwarded headers only from that proxy's actual IP addresses;
never trust arbitrary Internet clients. Otherwise redirect loops or spoofed scheme/IP
values can undermine HTTPS and rate-limit behavior. The application itself does not
interpret arbitrary X-Forwarded-Proto headers. See the official
[FastAPI proxy guidance](https://fastapi.tiangolo.com/advanced/behind-a-proxy/).
No services purchased, DNS changed, disk encryption enabled or public deployment made.

Remaining release decisions: HTTPS host/address, explicit proxy allowlist, persistent
protected storage, disk/backup encryption and recovery-key handling, supervised pilot.
Do not check off these operational items merely because configuration code exists.
