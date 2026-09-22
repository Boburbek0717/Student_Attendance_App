# Balance corrections and absence tracking

## Teacher workflow

On the teacher page choose **Change balance** beside a student. In the relevant
group, expand **Change remaining lesson count**, enter the desired total and a
reason, then save. Positive numbers mean lessons available, zero means no credit
or debt, and negative numbers mean lessons owed. Balances are whole numbers;
the technical input limit is ±1,000,000 lessons.

Example: a student has 8 lessons available. Entering 10 records a correction of
+2, not an extra purchase. Their next check-in leaves 9. A later renewal adds 12
normally. Setting a balance to -2 records two lessons owed; renewal leaves 10
available. Corrections are allowed for inactive memberships too.

**Balance correction history** records the teacher ID, UTC time, explanation,
old balance and new balance. A mistaken correction can be corrected again. The
original record stays visible. Passwords, attendance and purchase records are
not edited by a balance correction. The student sees the resulting balance and
the total correction, while detailed reasons stay on the teacher management page.

If attendance, renewal or another correction changes the balance after the page
was opened, saving asks the teacher to review the updated value first. Resubmitting
a successful correction cannot apply it twice. Saving the existing balance is a
no-op and does not create a misleading history entry.

## Absence on the lesson dashboard

Lesson details show **Present** for students with a code check-in and **Absent**
for expected students without one. These statuses appear immediately, including
while check-in is open. A later valid check-in changes absent to present on
refresh. Absence itself never deducts lessons. The group lesson list also shows
an absence count.

Starting a lesson saves the active enrollment IDs as that lesson's roster. Later
deactivations and new enrollments do not rewrite it. Reopening uses the same
saved roster. An active student enrolled after the start can still check in
under the existing rules and will appear as present.

Earlier lessons have no original roster. Their absence lists fall back to the
current active roster with a visible warning; we cannot reconstruct historical
enrollment reliably. We do not fabricate historical roster snapshots.

## Incremental concepts

The balance is now `purchased lessons + corrections - recorded attendance`.
`BalanceAdjustment` is an append-only record through the app: each row stores
the signed difference, not a new mutable remaining counter. Package credit is
reconciled with that total. Added credit covers owed lessons first; deductions
consume the oldest available credit first. Purchase limits and attendance counts
still describe the original records, so corrected remaining credit can exceed
a package's original allowance.

`LessonRosterSnapshot` records that a roster was captured, including an empty
roster. `LessonRoster` connects that lesson to its expected enrollments. Absence
is derived by comparing the saved roster with attendance; it does not need a
separate status that could contradict a later check-in.

Startup creates these three new tables through the existing table initializer.
No existing table or student data is replaced. New lesson creation and its roster
are saved in one transaction. Balance correction, attendance and renewal share
the existing serialized write transaction, and all teacher writes require CSRF.

Important files: `models.py` defines the records; `packages.py` calculates and
saves corrections; `student_management.py` handles the form; `attendance.py`
saves new lesson rosters; `lesson_management.py` derives present/absent lists.
`test_teacher_convenience.py` checks balance edits, late debt, renewal, stale
forms, permissions, concurrent corrections and membership changes.

Exercise: explain why absence should not be stored as an attendance row, and why
setting a balance to 10 twice should not add 20 lessons.
