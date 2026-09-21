# Lesson management

This stage adds a teacher view of each class. It uses the existing tables and
needs no migration or new dependency.

## Try the workflow

1. Sign in as a teacher and find a group on the teacher page.
2. Select **Manage lessons**. Lessons appear newest first, 25 per page, with their
   check-in status and recorded attendance count.
3. Open a lesson. An open lesson displays its code and expiry. Refresh the page
   after students check in to see their names and check-in times.
4. Choose **Close check-in** when everyone has finished. This immediately stops
   further submissions for that lesson. It does not cancel the lesson or refund
   any attendance.
5. If a student needs more time, open the same lesson and choose **Reopen check-in
   for this lesson**. Share the newly generated code. Its duration uses the same
   `ATTENDANCE_CODE_MINUTES` setting as starting a lesson.

Reopening preserves the original lesson date, attendance and package records.
A student who already attended cannot use another lesson credit by checking in
again. An exhausted package still follows the existing lessons-owed rule.
Another lesson in the same group must not have open check-in when reopening.

**Start a new lesson** still means a different class once the previous check-in
window closes. Use reopening when you mean to extend attendance for the same class.

## First concept: a lesson is different from its check-in window

`Lesson.id` identifies the class. The attendance code and its expiry only control
when students can submit attendance. Closing or reopening changes those two
fields, not the class ID or its `started_at` timestamp.

Closing clears both code fields in one transaction, satisfying the existing
database constraint. Reopening generates a random code that does not collide
with any currently active code. Expired codes still stored on that lesson are
excluded when generating its replacement. Codes can be reused over time; they
are temporary entry codes, not permanent identifiers.

## Second concept: relationships let us assemble a roster

The detail query follows `Lesson -> Attendance -> Enrollment -> User` to list
recorded attendees. An attendee remains visible even if their enrollment is
later deactivated. Display names and usernames reflect current profile values.

The second list shows **current active students without a check-in**. Enrollment
history is not dated in this app, so this is deliberately not labeled historical
absence. Someone who joined later may appear on that list for an earlier lesson.

## Third concept: coordinate changes from multiple browser tabs

Both close and reopen use the existing SQLite write transaction. Check-in and
lesson creation use the same mechanism. If a submission competes with closing,
it is either recorded before closing or rejected afterwards; there is no partial
attendance write.

The form also sends the code window that the teacher last viewed. If another tab
reopens the lesson, an old form cannot silently close the new window. A repeated
close is harmless, and a repeated reopen does not keep rotating the code.
This check is for stale forms; authorization comes separately from the teacher
session and CSRF validation.

## Files and routes

| File | Responsibility |
| --- | --- |
| `app/lesson_management.py` | Group lesson history, detail query, close/reopen transactions and routes |
| `app/attendance.py` | Shared active-code collision checks used by starting and reopening |
| `app/templates/lessons.html` | Paginated group lesson history |
| `app/templates/lesson.html` | Attendance lists, status and close/reopen forms |
| `app/templates/teacher.html` | Links from group cards and open lessons |
| `app/main.py` | Registers the lesson-management router |
| `tests/test_lesson_management.py` | Permissions, history, expiry, preserved records and simultaneous requests |

Routes:

- `GET /teacher/groups/{group_id}/lessons`: group history.
- `GET /teacher/lessons/{lesson_id}`: lesson details.
- `POST /teacher/lessons/{lesson_id}/close`: close check-in.
- `POST /teacher/lessons/{lesson_id}/reopen`: reopen the same lesson.

All are teacher-only. Both writes require a CSRF token. All teachers administer
the same business, consistent with the earlier stages. Refresh to update status;
there is no automatic live refresh.

Run the app with the command in the README; no setup changes are required.
The new tests use temporary databases and do not modify real students.

Exercise: A student checks in, the teacher closes the code, then reopens the same
lesson. Why does that student still have exactly one attendance row? Find the
database constraint and the application check that enforce this rule.
