from pathlib import Path
import re
import tempfile
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.create_user import create_user
from app.database import make_engine
from app.main import create_app
from app.models import Attendance, Enrollment, Group, Lesson, LessonPackage, User
from app.teacher import enroll_student


PASSWORD = "teacher-tests-only password"


class TeacherTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.engine = make_engine(str(Path(directory.name) / "test.db"))
        self.addCleanup(self.engine.dispose)
        self.client = self.enterContext(TestClient(create_app(self.engine, "test-secret")))
        with Session(self.engine) as db:
            self.teacher_id = create_user(db, "teacher", "Teacher", PASSWORD, "teacher").id
            self.student_id = create_user(db, "madina", "Madina", PASSWORD, "student").id
        self.login("teacher")

    def token(self, page):
        return re.search(r'name="csrf" value="([^"]+)"', page.text).group(1)

    def login(self, username):
        self.client.cookies.clear()
        csrf = self.token(self.client.get("/login"))
        self.client.post("/login", data={"username": username, "password": PASSWORD, "csrf": csrf})

    def post(self, path, **data):
        data["csrf"] = self.token(self.client.get("/teacher"))
        return self.client.post(path, data=data, follow_redirects=False)

    def group(self):
        self.post("/teacher/groups", group_name="SAT Advanced")
        with Session(self.engine) as db:
            return db.scalar(select(Group.id))

    def test_complete_setup_and_duplicate_enrollment(self):
        group_id = self.group()
        page = self.client.get("/teacher")
        self.assertIn('action="/teacher/groups"', page.text)
        self.assertIn('action="/teacher/students"', page.text)
        self.assertIn('action="/teacher/enrollments"', page.text)
        response = self.post("/teacher/enrollments", student_id=self.student_id, group_id=group_id)
        self.assertEqual(response.status_code, 303)
        page = self.client.get("/teacher")
        self.assertIn("0 / 12 lessons used", page.text)
        self.assertIn("12 remaining", page.text)
        response = self.post("/teacher/enrollments", student_id=self.student_id, group_id=group_id)
        self.assertEqual(response.status_code, 400)
        self.assertIn("already has an enrollment", response.text)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Enrollment)), 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(LessonPackage)), 1)

    def test_student_creation_cannot_assign_teacher_role_or_echo_password(self):
        response = self.post("/teacher/students", username="  ALI  ", display_name="Ali", password=PASSWORD,
                             confirm_password=PASSWORD, role="teacher")
        self.assertEqual(response.status_code, 303)
        with Session(self.engine) as db:
            user = db.scalar(select(User).where(User.username == "ali"))
            self.assertEqual(user.role, "student")
            self.assertNotEqual(user.password_hash, PASSWORD)
        response = self.post("/teacher/students", username="ali", display_name="Ali", password=PASSWORD,
                             confirm_password=PASSWORD)
        self.assertEqual(response.status_code, 400)
        self.assertIn("already in use", response.text)
        self.assertNotIn(PASSWORD, response.text)

    def test_invalid_group_and_student_validation_are_visible(self):
        self.assertIn("Enter a group name", self.post("/teacher/groups", group_name=" ").text)
        response = self.post("/teacher/students", username="ali", display_name="Ali",
                             password=PASSWORD, confirm_password="different")
        self.assertEqual(response.status_code, 400)
        self.assertIn("passwords do not match", response.text)
        self.assertNotIn(PASSWORD, response.text)

    def test_all_writes_require_teacher_and_csrf(self):
        for path in ("/teacher/groups", "/teacher/students", "/teacher/enrollments"):
            self.assertEqual(self.client.post(path, data={}).status_code, 403)
        self.login("madina")
        csrf = self.token(self.client.get("/student"))
        for path in ("/teacher/groups", "/teacher/students", "/teacher/enrollments"):
            self.assertEqual(self.client.post(path, data={"csrf": csrf}).status_code, 403)
        self.client.cookies.clear()
        for path in ("/teacher/groups", "/teacher/students", "/teacher/enrollments"):
            self.assertEqual(self.client.post(path, data={}, follow_redirects=False).status_code, 303)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Group)), 0)
            self.assertEqual(db.scalar(select(func.count()).select_from(User)), 2)

    def test_invalid_memberships_do_not_create_packages(self):
        group_id = self.group()
        for student_id, chosen_group in ((self.teacher_id, group_id), (999, group_id),
                                         (self.student_id, 999), ("bad", group_id),
                                         (str(2**100), group_id)):
            response = self.post("/teacher/enrollments", student_id=student_id, group_id=chosen_group)
            self.assertEqual(response.status_code, 400)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(LessonPackage)), 0)

    def test_failed_package_insert_rolls_back_membership(self):
        group_id = self.group()

        def fail(mapper, connection, target):
            raise IntegrityError("test package failure", {}, Exception("forced failure"))

        event.listen(LessonPackage, "before_insert", fail)
        try:
            with Session(self.engine) as db:
                with self.assertRaises(ValueError):
                    enroll_student(db, str(self.student_id), str(group_id))
                self.assertEqual(db.scalar(select(func.count()).select_from(Enrollment)), 0)
                self.assertEqual(db.scalar(select(func.count()).select_from(LessonPackage)), 0)
        finally:
            event.remove(LessonPackage, "before_insert", fail)

    def test_balances_use_attendance_and_keep_packages_separate(self):
        group_id = self.group()
        self.post("/teacher/enrollments", student_id=self.student_id, group_id=group_id)
        with Session(self.engine) as db:
            enrollment = db.scalar(select(Enrollment))
            package = db.scalar(select(LessonPackage))
            lesson = Lesson(group_id=group_id)
            db.add(lesson)
            db.flush()
            db.add(Attendance(lesson_id=lesson.id, enrollment_id=enrollment.id, package_id=package.id))
            db.add(LessonPackage(enrollment_id=enrollment.id))
            db.commit()
        page = self.client.get("/teacher")
        self.assertIn("1 / 12 lessons used", page.text)
        self.assertIn("11 remaining", page.text)
        self.assertIn("0 / 12 lessons used", page.text)
        self.assertIn("12 remaining", page.text)

    def test_group_names_are_escaped(self):
        self.post("/teacher/groups", group_name="<script>alert(1)</script>")
        page = self.client.get("/teacher")
        self.assertNotIn("<script>", page.text)
        self.assertIn("&lt;script&gt;", page.text)
