# Teacher renewal and early/late lesson accounting

The teacher records renewals manually after handling payment outside the app.
Students cannot renew, pay, or edit balances. Each confirmation adds exactly one
new 12-lesson package to one active student/group enrollment.

## How to use it

Open the teacher page, find the student in their group, and choose **Renew package**.
The dedicated page shows the student, group, current counters and the result of
adding 12 lessons. Confirm to save, or return without making a change. The same
link is available on the teacher's student-history page.

| Situation | Before | After one renewal |
| --- | --- | --- |
| Early payment | 4 available, 0 owed | 16 available, including 12 in a later package |
| On time | 0 available, 0 owed | 12 available, 0 owed |
| Two lessons late | 0 available, 2 owed | 10 available, 0 owed |
| Fourteen lessons late | 0 available, 14 owed | 0 available, 2 still owed |

The app records lesson credit, not money, invoices or payment status. Initial
enrollment still includes 12 lessons. An account with no package at all cannot
check in until the teacher grants its first package. Inactive memberships cannot
check in or renew. Owed lessons have no automatic cap under the chosen policy.

## One source of truth

For each enrollment:

```text
net balance = sum(package lesson allowances) - count(attendance)
available = max(net balance, 0)
owed = max(-net balance, 0)
```

Available includes any queued credit. The advance counter shows unused lessons
in packages after the oldest package with credit. It is a subset of available,
not an amount to add again. All counters are calculated; none are manually stored.

Check-in consumes the oldest package with usable credit. If every package is
exhausted, attendance stays linked to the latest package and increases the owed
counter. Duplicate check-in for the same lesson is still rejected.

When a new package is added, earlier excess is carried into its calculation:

```text
Package 1: 12 included, 14 attendance records -> 2 carried forward
Package 2: 12 included, 0 new attendance, 2 carried in -> 10 remaining
```

The 14 original records stay attached to package 1, with unchanged dates and IDs.
Package history labels the carry-over so its remaining amount is understandable.
It is now valid for a historical package to have more attendance records than its
allowance. That means late attendance, not database corruption. A further check-in
uses package 2 and leaves 9 lessons. An enrollment's current owed counter is the
authoritative outstanding amount; historical carry-over notes must not be summed.

## Preventing double renewal

The preview carries the latest package ID and attendance count it was based on.
When the teacher confirms, the backend reserves SQLite's writer and checks those
values again before inserting the package. If a renewal or check-in happened
meanwhile, the page shows the updated balance and requires a fresh confirmation.
Submitting one form twice or submitting two previews made at the same time can
therefore add only one package. Intentionally opening a new preview after success
allows another manual renewal.

This is an **optimistic concurrency check**: proceed only if the facts reviewed by
the teacher are still current. It complements the write transaction, which keeps
the check and save together. The hidden values are not permissions; every request
also checks the logged-in teacher and its CSRF token.

## Files and tests

- `app/packages.py` centralizes counter calculation and renewal validation.
- `app/database.py` now owns the shared serialized write-transaction helper.
- `app/attendance.py` uses those counters and permits late attendance.
- `app/teacher.py` exposes teacher-only GET preview and POST confirmation routes.
- `lesson_balance.html` shares the counters between teacher and student pages.
- `renew_package.html` presents the review step; no JavaScript is required.
- `tests/test_packages.py` adds 11 tests, including duplicate submissions,
  simultaneous renewal/check-in, group isolation and unchanged attendance history.

The earlier tests rejecting an exhausted package were deliberately updated to
the newly requested rule: attendance is allowed and counted as owed. Two different
lessons arriving with one credit left record one paid and one owed lesson; two
requests for the same lesson still record just one attendance.

No new dependencies or schema migration are needed. Tests use isolated databases;
the implementation does not add credits or alter records in the real database
until the teacher uses the renewal feature.

Exercise: a student has 26 attendance records against one package of 12. Predict
the available/owed counters after one renewal and then after a second renewal.
