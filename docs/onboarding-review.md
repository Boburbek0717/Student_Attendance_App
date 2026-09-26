# SF-14 — First-class account guidance

Owner decision: keep teacher-issued passwords and teacher-managed resets. No
self-service signup, recovery endpoint, temporary-password state or forced-change
workflow added. Teacher verifies identity using their existing private contact
with the student, confirms the username or resets through Manage students, and
shares the new password privately. Existing reset revocation signs out old sessions.

Delivered in this bounded chunk:
- Native expandable first-login/recovery help on login; opens after login errors.
- Missing-enrollment notice before check-in, plus inactive-membership guidance.
- Current-code instructions and expandable help for expiry, dropped connections,
  same-form retries, already-recorded attendance and teacher corrections.
- Teacher reset reminder to verify identity and avoid group-chat disclosure.

No contact address was invented, and no account-existence lookup was introduced.
Success/duplicate notices and attendance accounting remain unchanged. No passwords
are added to URLs, logs, documentation or screenshots. Help works without JavaScript.

Verification with project Python and guarded runner:
`python scripts/verify.py --pattern test_onboarding.py`: 2 passed, 0.693s.
`python scripts/verify.py --pattern test_student_management.py`: 9 passed, 3.807s,
including role/CSRF controls and actual old-cookie rejection after password reset.
New checks cover generic known/unknown-account failures, missing/inactive enrollment,
student denial of teacher management, and recovery help. Existing full-suite and
polling evidence remains in pilot-handover.md; no claim of a new full-suite run.

Static Jinja browser previews (no app/database import) checked login at 390px and
student at 320px. Enter expands both help controls; keyboard focus is visible;
no page overflow (375/375 and 305/305 content/scroll widths). Screenshots contain
fictional or blank information only. Login preview: output/onboarding-help.png.
These are simulated browser checks, not first-time real-user validation.

Owner review: pending. Ask a consenting first-time student to obtain credentials,
log in on a phone, locate their group, submit a code, and explain what they would
do after a failed login or uncertain check-in. Record confusion before calling
SF-14 Done. Current status: implementation ready for review; real-user criterion open.

Next separate chunk: SF-13 production configuration/release preparation. Hosting,
public address, off-laptop backup access and actual deployment remain undecided.
