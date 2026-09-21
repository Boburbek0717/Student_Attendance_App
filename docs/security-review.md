# Security and correctness review

This records the review before the attendance stage. The later attendance stage
implements and tests the check-in rules listed below as future work; see
[attendance.md](attendance.md) for the current behavior and 60-test suite.

Reviewed the current source, including the interrupted teacher implementation,
using isolated database/HTTP tests, source inspection, installed-package checks
and PyPI vulnerability metadata. Tests do not modify real student records.

## Confirmed findings — fixed

| Severity | Reproduced problem | Fix |
| --- | --- | --- |
| High | A copied cookie returned HTTP 200 on a protected page after logout. | Database-backed login sessions are revoked on logout. Replayed cookies now redirect to login. |
| High | SQLite reused a deleted user's ID, and the old cookie authenticated as the replacement account. | Deleting a user removes their login sessions. A reused ID cannot revive an old session. |
| Medium | Login allowed repeated expensive password checks without an attempt limit. | Ten attempts per connection address per minute, checked before password verification, with HTTP 429 and Retry-After. |
| Medium | Form bodies had no application-wide size bound before parsing. | A 16 KiB limit rejects oversized ordinary and streamed bodies with HTTP 413. |
| Medium | Teacher routes still rendered a placeholder, hiding forms, validation errors and results. | Connected the routes to forms and rosters; tested permissions, duplicate enrollment, forged role fields and transaction rollback. |

Password changes now invalidate existing sessions. Database session expiry is
enforced independently of cookie expiry. HTML responses restrict framing and form
destinations. Existing password hashing, CSRF checks, parameterized queries and
HTML escaping remain in place.

## Verification

- All 40 tests passed: 23 authentication/security, 9 database and 8 teacher tests.
- `pip check` found no broken installed dependency requirements.
- All 27 pinned versions were checked against PyPI's version JSON metadata. None
  reported published vulnerabilities at the timestamp in
  [dependency-audit.json](dependency-audit.json). This cannot rule out undiscovered
  vulnerabilities or problems not covered by that advisory source.
- Git does not track the local database, signing key or environment secrets.
- Startup adds a login-session table without changing the six business tables.

## Remaining limits

- Local HTTP only: HTTPS-only cookies and deployment configuration remain future
  work before public hosting.
- Login limiting is per process and connection address, resets on restart, and
  has bounded memory. It is not distributed attack protection. Run local Uvicorn
  with `--no-proxy-headers` so forwarded headers cannot choose the limiting key.
- All teachers administer the same business. Separate teacher/business ownership
  is not part of this design.
- Check-in is not implemented. Active membership, same-group attendance, available
  package capacity and concurrent spending require application checks and tests
  when check-in is added. The schema alone is insufficient.
- There are no account deletion or password-reset routes. Their session effects
  were tested through direct changes in isolated databases.
- This was a code/dependency review with targeted tests, not a complete penetration
  test or an audit of the computer's permissions and network configuration.

Dependency source: [PyPI JSON API](https://docs.pypi.org/api/json/).
