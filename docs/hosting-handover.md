# Hosting handover — 2026-10-10

Scope: SF-13 free portfolio demonstration, not a real-course production release.

## Verified deployment

- URL: https://sat-factory-portfolio-demo.onrender.com/
- Service: `srv-db3tin6b7d7c739j1qe0`, Python 3, Free.
- Blueprint: `exs-db3tik8473hc73btlc2g` (SAT Factory Portfolio Demo).
- Source: `Boburbek0717/Student_Attendance_App`, branch `master`.
- Deployed application: `81a5125d87c708e6b5d48d2927a77191d28631dd`.
- Render reports Live; initial build/deploy took 1m24s.
- Automatic application deployments are off in render.yaml. Documentation commits
  after this release do not require an application redeployment.
- The old empty IELTS-ESSAY-BOT project was deleted following explicit owner confirmation.
- No paid storage, domain, database or additional service was provisioned.

This replaces the earlier proposal to deploy the older `portfolio-demo` branch.
All pending implementation changes were committed and pushed to master first.

## Evidence

Pre-deployment isolated verification at the released code:
`.venv\Scripts\python.exe scripts/check.py`
passed 273 Python tests, 22 Node checks, dependency consistency and whitespace checks.
Log: ignored `output/pre-hosting-check-final.txt`. No application code changed during
this final deployment check; the full suite was not repeated for documentation edits.

Live verification on October 10:
- Browser teacher and student login successful; fictional dashboards rendered.
- Student assignment answer B (5) saved as correct, attempt 1.
- Public HTTP probes using Python standard-library urllib: `/healthz` 200 `ok`,
  `/docs` 404, `/robots.txt` 200, unauthenticated teacher/student routes 303.
- Login response cookie includes Secure, HttpOnly, SameSite=lax; CSP,
  X-Content-Type-Options and HSTS present. Cookie values were not recorded.
- Disallowed POST `/teacher/questions` 403; login POST without CSRF 403.
- HTTP homepage redirects 301 to HTTPS.
- Render Restart service event confirmed. The previous teacher session then
  redirected to login; a fresh student login succeeded, balance was 11 and the
  assignment returned to 0/3, all questions not attempted.

These are deployment smoke checks, not a load test, exhaustive security audit or
real-device/classroom acceptance. Attendance concurrency has automated coverage;
a full multi-student classroom rehearsal was not repeated on the public service.

## Operations and limitations

The login page displays intentionally public demo credentials. Do not reuse them
for real accounts or enter personal information. Course records are fictional and
shared. Uploaded question PDFs and the working database were not deployed.
The existing public homepage/results content remains included.

Free instances sleep with inactivity; Render warns cold starts can take 50 seconds
or more. Every process restart rebuilds fictional records and rotates the session
secret. Content editing, account creation and uploads are unavailable; traffic and
writes have shared limits. This is not persistent production storage or a backup.

To reset exhausted/changed demo data: service dashboard > Manual Deploy > Restart
service. To release application changes: run scripts/check.py in the isolated
runner, commit/push, then use Manual Deploy for the reviewed commit and repeat
health/login checks. Do not switch this temporary demo launcher to live records.

Working tree was clean and synced at 81a5125 before this documentation checkpoint.
Next: owner portfolio walkthrough. Production hosting, persistent storage and
course readiness remain separate decisions; no owner acceptance is claimed.
