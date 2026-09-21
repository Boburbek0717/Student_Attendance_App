# Student management

Open the teacher page and choose **Manage students**. Search by display name or
username, then open a student. Students with no enrollments are included. Group
rosters and student-history pages also link to the management page.

## The new concepts

**Identity is different from a name.** Updating a display name or username keeps
the student's database ID. Packages, enrollments and attendance refer to that ID,
so editing a name does not detach or recreate history. Usernames remain unique,
trimmed and lowercased. A changed username must be communicated to the student.
Their existing sessions remain signed in unless the password is reset.

**Deactivation is different from deletion.** An enrollment's active flag controls
whether that student may check in or renew in that group. Turning it off preserves
available lessons, owed lessons, packages and history. Turning it on restores the
same membership without adding credit. The account can still log in and view old
records, and memberships in other groups are unaffected.

**Password reset revokes access already granted.** The new password is hashed with
Argon2. The password change and deletion of that student's login-session records
happen in one transaction. Previously copied cookies are rejected afterward.
Other accounts remain signed in. The form never displays or stores a plaintext
password; the teacher shares the new password privately outside the app. There is
no emailed reset link, student self-service reset or forced-change screen yet.

## Routes and files

`app/student_management.py` contains the teacher-only router and its small service
functions. The router is registered in `app/main.py`. It uses the existing shared
database transaction helper and teacher-role dependency.

| Action | Route |
| --- | --- |
| Directory/search | GET `/teacher/students?q=...` |
| View controls | GET `/teacher/students/{id}/manage` |
| Update profile | POST `/teacher/students/{id}/profile` |
| Reset password | POST `/teacher/students/{id}/password` |
| Set enrollment status | POST `/teacher/students/{id}/enrollments/{enrollment_id}/status` |

Every write checks teacher permissions and the CSRF token. The target must be a
student account, and the selected enrollment must belong to that student. Search
values are bound query parameters; wildcard characters are treated literally.
Profile forms include their original name and username so an old tab cannot
silently overwrite a more recent edit. On errors the form shows current saved
details. Password fields always return empty.

The status form sends the explicit desired state instead of a toggle. Repeating
“deactivate” leaves the membership inactive; it does not accidentally reactivate it.
This is **idempotence**: repeating the same operation has the same final result.

`students.html` renders the directory, while `manage_student.html` contains profile,
password and membership controls. It reuses the existing balance component.
No new dependencies or database migration are needed.

## Checks and a small exercise

Nine new tests cover search, normalized/duplicate/stale profile edits, safe password
reset and cookie revocation, invalid passwords, enrollment deactivation/reactivation,
wrong enrollment ownership, role/CSRF protection and HTML escaping. The full suite
has 80 tests, all using isolated databases rather than real student accounts.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Exercise: deactivate and reactivate a test student's enrollment. Predict whether
their lesson balance changes, then inspect the code to explain why it does not.
Resetting passwords and managing profiles remain teacher responsibilities; this
stage does not add account deletion or separate ownership between teachers.
