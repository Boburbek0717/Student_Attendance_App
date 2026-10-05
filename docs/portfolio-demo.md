# Portfolio demo: local preparation

Scope: SF-13 demo preparation, separate from the postponed course launch.

Run from the repository using Python 3.14 and the installed project dependencies:

```powershell
.venv\Scripts\python.exe scripts/portfolio_demo.py
```

Open http://127.0.0.1:8767/login. The page displays intentionally public demo
credentials. Use demo-teacher or demo-student with Explore-SAT-Factory!.
These credentials must never be reused for real accounts.

The demo contains six fictional students, one group, twelve-lesson purchases,
a finished lesson (four present, two absent), three original sample questions
in separate categories, and a three-question assignment. No imported PDF content
or real student accounts are copied. Existing public homepage/results content is
unchanged. The banner identifies the shared sandbox on every application page.

Suggested walkthrough:
1. Log in as the student, inspect the 11 remaining lessons and assignment.
2. Try a question, its feedback and the assignment flow; set a target score.
3. Log out, enter as the teacher, inspect the completed lesson and start a new one.
4. Share its code with another browser signed in as the demo student.
5. Inspect attendance and try a renewal or correction.
6. Try a password reset or enrollment deactivation: demo access is protected.

All writes go to a generated temporary directory. There is no configurable
existing database path. The import guard blocks the normal database engine and
redirects the session-secret path for the full lifetime. A separate cookie avoids
replacing a course login on the same hostname. Restarting generates a fresh database
and secret; previous sessions no longer work. Ctrl+C performs normal cleanup.
A forced process termination may leave a temporary directory; it is never reused.

Account profile/password and enrollment-status writes are blocked by a demo-only
middleware. Ordinary application authentication, CSRF and role checks still apply.
Other sandbox edits are shared: this is not a private workspace per visitor.
Do not enter personal data. Restart locally to recover any altered demonstration.

## Not yet a public-hosting entry point

This launcher binds only to loopback and uses local HTTP. Do not expose it through
a tunnel or change its bind address as a shortcut to deployment. The next chunk
must prepare HTTPS/proxy/host configuration, health checks, bounded public writes
and upload behavior, shared-login rate limits, resource caps and reset strategy.
Review free-host constraints and decide how simultaneous visitors share activity
before publication. No Render resources, billing, external storage or schedule
have been created. No public uptime or real-phone acceptance is claimed.

Verification uses `scripts/verify.py --pattern test_portfolio_demo.py`.
Tests cover seeding/foreign keys, student and teacher access, role denial,
protected mutations, CSRF, target writes, refusing reseeding existing data, and
fresh storage/session invalidation on restart.

## Free Render hosting configuration (prepared, not deployed)

`render.yaml` selects one free Python web service, no database service, no persistent
disk and no automatic deploy on commit. Python is pinned to 3.14.7. Build:
`pip install -r requirements.txt`. Start: `python scripts/demo_host.py`.
Health check: `/healthz`. No secret or real database is uploaded: each process
creates a new random session secret and disposable fictional database.

Render supplies `RENDER=true`, `RENDER_EXTERNAL_HOSTNAME` and `PORT`;
the Blueprint explicitly supplies `SAT_FACTORY_PUBLIC_DEMO=1`. Startup refuses
missing opt-in, invalid public hostname or invalid port. Do not set
SAT_FACTORY_ENV=production for this launcher: it explicitly constructs the guarded
public app in production mode, independently of the ordinary module-level app.
Only the Render hostname and local health-check hostnames are accepted.

Render terminates HTTPS. The launcher trusts forwarded headers only under this
Render-specific operating arrangement (matching Render's default Python proxy
setting). Do not reuse it on a directly reachable VPS. Secure cookies, HTTPS
redirects, host validation and security headers apply. Access logs are disabled;
application startup/error logs remain. `/robots.txt` discourages indexing; it is
not access control. `/healthz` returns only `ok` or a generic 503 and tests a DB read.

Public demo edits are explicitly allowlisted: login/logout, student target,
check-in, practice/bookmarks, assignment answers, lesson start/close/reopen/finish,
and renewal. Existing auth, CSRF, retry, role and permanent-finish checks still run.
Account/group/enrollment creation, profile/password/status changes, PDF imports,
question authoring/publication, assignment creation and balance corrections are
unavailable in this public slice. Their existing pages remain inspectable; submitting
blocked forms returns a clear 403. Local demo behavior remains unchanged.

Resource limits for this small shared demo:
- One worker; at most 20 concurrent connections/tasks admitted by Uvicorn.
- 300 dynamic requests and 60 write requests per rolling minute, globally shared.
- 5,000 admitted write requests per process lifetime, including failed logins and
  invalid forms; after that browsing remains available, writes return 503 until restart.
- Static files and health probes bypass the application rate counters.
- Rejected uploads are blocked before buffering. Existing normal form-size limits apply.
- Existing per-account login/answer limits also apply; public credentials do not bypass them.

These limits bound normal application work, not all network costs or denial of service.
Visitors share progress and capacity; an abusive visitor can temporarily exhaust
access. The owner can manually restart/redeploy to reset. No automatic reset job,
keep-awake service, extra storage, or scheduling is configured.

### Publication checklist, after owner approval

1. Push the reviewed demo commits; create a Render Blueprint from this GitHub repo.
   Creating the Blueprint publishes the service: do not apply as a mere validation.
2. Confirm the Free service plan, Hobby workspace and no paid add-ons before creation.
   Check account usage limits/billing; free service does not mean unlimited bandwidth.
3. Inspect the Linux dependency build. Linux dependency installation and real proxy
   behavior have not been tested locally on this Windows machine.
4. Verify health over the assigned HTTPS URL, no redirect loop, secure cookie,
   correct host rejection, both demo logins, questions, assignments, lesson check-in,
   blocked uploads/content changes, and friendly rate-limit responses.
5. Restart once: seed returns, previous sessions are invalid, existing local course
   data remains untouched. Test cold start on a phone. Record evidence and URL.
6. Link the demo from the README only after these checks pass. Roll back by selecting
   a known demo-enabled commit; every deployment resets fictional activity.

Render Free sleeps after 15 idle minutes, can take about a minute to wake, and loses
local files on restart/redeploy/sleep. It provides 750 free instance hours per
workspace/month; bandwidth/build overages can cost money if billing is enabled,
or cause suspension when no payment method is present. No course data belongs here.

Official references checked 2026-10-06:
- https://render.com/docs/free
- https://render.com/docs/deploy-fastapi
- https://render.com/docs/python-version
- https://render.com/docs/environment-variables
- https://render.com/docs/blueprint-spec

Prepared configuration is not proof of a successful host deployment. Remaining:
owner publication approval, remote push, account/provider validation, Linux build,
real proxy/health probe behavior and public browser smoke test.
