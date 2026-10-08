# Hosting handover — 2026-10-08

Scope: publish the fictional free Render demo, authorized by owner continuation.
Current main checkout: 97deffe with existing uncommitted PDF/image work preserved.
Selected release: 32b5d2e0b9832182ab9ab47931ae271f350099f4, the reviewed hosting
checkpoint; newer PDF/guest-practice work is deliberately outside this first release.

Exported that commit with git archive into ignored output/hosting-release-20261008/source.
Ran using the project virtualenv, against the exported snapshot:
- scripts/verify.py --pattern test_demo_host.py: 3 passed (0.568s).
- scripts/verify.py --pattern test_portfolio_demo.py: 3 passed (1.509s).
Both guarded runners used fictional temporary databases; no working records read.

Pushed exactly 32b5d2e to new origin/portfolio-demo. Remote hash confirmed matches.
Master and uncommitted work were not pushed or altered. No PR created.

Render requires interactive account sign-in; browser was left at the owner's
GitHub sign-in flow for Render. Do not read credentials. No Render service created,
terms accepted, payment added, public deployment or build success claimed.

Next: after owner login, create the Free web service from the portfolio-demo branch
of Boburbek0717/Student_Attendance_App. Explicitly select that branch (not master).
Build pip install -r requirements.txt; start python scripts/demo_host.py;
PYTHON_VERSION=3.14.7, SAT_FACTORY_PUBLIC_DEMO=1; health /healthz; disable auto-deploy.
Use free/Hobby options only, no payment/domain/storage purchase. Verify actual
Linux build, HTTPS proxy, health, both logins, interactive practice, blocked actions
and restart reset before linking a live demo. Prepared Blueprint is on that branch.
