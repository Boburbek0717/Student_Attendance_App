from pathlib import Path
import re
import tempfile
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.attendance import check_in, start_lesson
from app.database import make_engine
from app.main import create_app
from app.models import Attendance, Enrollment, Group, Lesson, LessonPackage, LoginSession, User
from app.packages import package_balance, package_rows, renew_package
from app.security import password_hasher


PASSWORD = "old test-only passphrase"
NEW_PASSWORD = "new test-only passphrase"


class StudentManagementTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.engine = make_engine(str(Path(directory.name) / "test.db"))
        self.addCleanup(self.engine.dispose)
        app = create_app(self.engine, "test-secret")
        self.teacher = self.enterContext(TestClient(app))
        self.student = self.enterContext(TestClient(app))
        with Session(self.engine) as db:
            hashed = password_hasher.hash(PASSWORD)
            teacher = User(username="teacher", display_name="Teacher", role="teacher", password_hash=hashed)
            student = User(username="madina", display_name="Madina", role="student", password_hash=hashed)
            other = User(username="other", display_name="Other Student", role="student", password_hash=hashed)
            first, second = Group(name="SAT"), Group(name="IELTS")
            db.add_all([teacher, student, other, first, second])
            db.flush()
            self.teacher_id, self.student_id, self.other_id = teacher.id, student.id, other.id
            self.group_id = first.id
            enrollment = Enrollment(student_id=student.id, group_id=first.id)
            other_membership = Enrollment(student_id=other.id, group_id=second.id)
            db.add_all([enrollment, other_membership])
            db.flush()
            self.enrollment_id, self.other_enrollment_id = enrollment.id, other_membership.id
            db.add(LessonPackage(enrollment_id=enrollment.id))
            db.commit()
        self.base = f"/teacher/students/{self.student_id}"
        self.login(self.teacher, "teacher")
        self.login(self.student, "madina")

    def field(self, page, name):
        return re.search(fr'name="{name}" value="([^"]*)"', page.text).group(1)

    def login(self, client, username, password=PASSWORD):
        client.cookies.clear()
        csrf = self.field(client.get("/login"), "csrf")
        return client.post("/login", data={"username": username, "password": password, "csrf": csrf}, follow_redirects=False)

    def submit(self, suffix, **data):
        data["csrf"] = self.field(self.teacher.get(self.base + "/manage"), "csrf")
        return self.teacher.post(self.base + suffix, data=data, follow_redirects=False)

    def test_directory_and_search(self):
        page = self.teacher.get("/teacher/students")
        self.assertIn("Madina", page.text)
        self.assertIn("Other Student", page.text)
        self.assertIn("Madina", self.teacher.get("/teacher/students?q=MADINA").text)
        self.assertNotIn("Other Student", self.teacher.get("/teacher/students?q=madina").text)
        self.assertIn("No students found", self.teacher.get("/teacher/students?q=%25").text)
        self.assertIn("Manage students", self.teacher.get("/teacher").text)

    def test_update_normalizes_username_preserves_identity_and_history(self):
        response = self.submit("/profile", username=" MADINA.NEW ", display_name=" Madina Updated ",
                               expected_username="madina", expected_name="Madina", role="teacher")
        self.assertEqual(response.status_code, 303)
        with Session(self.engine) as db:
            user = db.get(User, self.student_id)
            self.assertEqual((user.username, user.display_name, user.role), ("madina.new", "Madina Updated", "student"))
            self.assertEqual(db.get(Enrollment, self.enrollment_id).student_id, self.student_id)
            self.assertEqual(db.scalar(select(func.count()).select_from(LessonPackage)), 1)
        self.assertEqual(self.login(self.student, "madina").status_code, 401)
        self.assertEqual(self.login(self.student, "madina.new").status_code, 303)

    def test_duplicate_invalid_and_stale_profile_edits(self):
        for username, name in (("teacher", "Changed"), ("bad name", "Changed"), ("madina", " ")):
            response = self.submit("/profile", username=username, display_name=name,
                                   expected_username="madina", expected_name="Madina")
            self.assertEqual(response.status_code, 400)
        response = self.submit("/profile", username="madina", display_name="Changed",
                               expected_username="madina", expected_name="Old name")
        self.assertEqual(response.status_code, 400)
        self.assertIn("profile changed", response.text)
        with Session(self.engine) as db:
            self.assertEqual(db.get(User, self.student_id).display_name, "Madina")

    def test_password_reset_revokes_existing_cookie_and_changes_credentials(self):
        copied_cookie = self.student.cookies["attendance_session"]
        response = self.submit("/password", password=NEW_PASSWORD, confirm_password=NEW_PASSWORD)
        self.assertEqual(response.status_code, 303)
        self.student.cookies.clear()
        self.student.cookies.set("attendance_session", copied_cookie)
        self.assertEqual(self.student.get("/student", follow_redirects=False).status_code, 303)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(LoginSession).where(LoginSession.user_id == self.student_id)), 0)
            self.assertTrue(password_hasher.verify(NEW_PASSWORD, db.get(User, self.student_id).password_hash))
        self.assertEqual(self.login(self.student, "madina", PASSWORD).status_code, 401)
        self.assertEqual(self.login(self.student, "madina", NEW_PASSWORD).status_code, 303)
        self.assertEqual(self.teacher.get(self.base + "/manage").status_code, 200)

    def test_bad_password_reset_never_echoes_password_or_revokes_login(self):
        for password, confirmation in ((NEW_PASSWORD, "mismatch"), ("short", "short"), ("x" * 129, "x" * 129)):
            response = self.submit("/password", password=password, confirm_password=confirmation)
            self.assertEqual(response.status_code, 400)
            self.assertNotIn(password, response.text)
        self.assertEqual(self.student.get("/student").status_code, 200)

    def test_deactivate_reactivate_preserves_package_and_history(self):
        lesson_id = start_lesson(self.engine, self.teacher_id, self.group_id)
        with Session(self.engine) as db:
            code = db.get(Lesson, lesson_id).attendance_code
        check_in(self.engine, self.student_id, code)
        with Session(self.engine) as db:
            before = db.execute(select(Attendance.id, Attendance.package_id, Attendance.checked_in_at)).all()
            balance = package_balance(package_rows(db, self.enrollment_id))
        path = f"/enrollments/{self.enrollment_id}/status"
        for _ in range(2):
            self.assertEqual(self.submit(path, active="false").status_code, 303)
        with self.assertRaisesRegex(ValueError, "active enrollment"):
            check_in(self.engine, self.student_id, code)
        with self.assertRaisesRegex(ValueError, "active enrollment"):
            renew_package(self.engine, self.teacher_id, self.enrollment_id, balance["latest_package_id"], balance["attended"])
        self.assertIn("Inactive enrollment", self.student.get("/student").text)
        for _ in range(2):
            self.assertEqual(self.submit(path, active="true").status_code, 303)
        with Session(self.engine) as db:
            self.assertTrue(db.get(Enrollment, self.enrollment_id).active)
            self.assertEqual(db.execute(select(Attendance.id, Attendance.package_id, Attendance.checked_in_at)).all(), before)
            self.assertEqual(package_balance(package_rows(db, self.enrollment_id)), balance)
        with self.assertRaisesRegex(ValueError, "already checked in"):
            check_in(self.engine, self.student_id, code)

    def test_wrong_enrollment_and_teacher_targets_rejected(self):
        response = self.submit(f"/enrollments/{self.other_enrollment_id}/status", active="false")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.teacher.get(f"/teacher/students/{self.teacher_id}/manage").status_code, 404)
        csrf = self.field(self.teacher.get(self.base + "/manage"), "csrf")
        response = self.teacher.post(f"/teacher/students/{self.teacher_id}/password",
                                     data={"csrf": csrf, "password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.teacher.get("/teacher/students/999999999999999999999999/manage").status_code, 404)
        self.assertEqual(self.submit(f"/enrollments/{self.enrollment_id}/status", active="bad").status_code, 400)

    def test_all_mutations_require_teacher_and_csrf(self):
        paths = (self.base + "/profile", self.base + "/password", self.base + f"/enrollments/{self.enrollment_id}/status")
        for path in paths:
            self.assertEqual(self.teacher.post(path).status_code, 403)
            self.assertEqual(self.student.post(path).status_code, 403)
            self.assertEqual(self.teacher.get(path).status_code, 405)
        self.assertEqual(self.student.get("/teacher/students").status_code, 403)
        self.assertEqual(self.student.get(self.base + "/manage").status_code, 403)
        self.teacher.cookies.clear()
        for path in paths:
            self.assertEqual(self.teacher.post(path, follow_redirects=False).status_code, 303)

    def test_names_are_escaped_on_management_page(self):
        response = self.submit("/profile", username="madina", display_name="<script>alert(1)</script>",
                               expected_username="madina", expected_name="Madina")
        self.assertEqual(response.status_code, 303)
        page = self.teacher.get(self.base + "/manage")
        self.assertNotIn("<script>", page.text)
        self.assertIn("&lt;script&gt;", page.text)
