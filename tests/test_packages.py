from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Barrier
import re
import tempfile
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.attendance import check_in
from app.database import initialize_database, make_engine
from app.main import create_app
from app.models import Attendance, Enrollment, Group, Lesson, LessonPackage, User, utc_now
from app.packages import package_balance, package_rows, renew_package
from app.security import password_hasher


class RenewalRulesTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.engine = make_engine(str(Path(directory.name) / "test.db"))
        self.addCleanup(self.engine.dispose)
        initialize_database(self.engine)
        with Session(self.engine) as db:
            teacher = User(username="teacher", display_name="Teacher", role="teacher", password_hash="test")
            student = User(username="student", display_name="Student", role="student", password_hash="test")
            group, other = Group(name="SAT"), Group(name="IELTS")
            db.add_all([teacher, student, group, other])
            db.flush()
            self.teacher_id, self.student_id = teacher.id, student.id
            self.group_id = group.id
            first = Enrollment(student_id=student.id, group_id=group.id)
            second = Enrollment(student_id=student.id, group_id=other.id)
            db.add_all([first, second])
            db.flush()
            self.enrollment_id, self.other_enrollment_id = first.id, second.id
            package = LessonPackage(enrollment_id=first.id)
            db.add_all([package, LessonPackage(enrollment_id=second.id)])
            db.flush()
            self.package_id = package.id
            db.commit()

    def balance(self, enrollment_id=None):
        with Session(self.engine) as db:
            return package_balance(package_rows(db, enrollment_id or self.enrollment_id))

    def renew(self, snapshot=None):
        snapshot = snapshot or self.balance()
        return renew_package(self.engine, self.teacher_id, self.enrollment_id,
                             snapshot["latest_package_id"], snapshot["attended"])

    def fill(self, count):
        with Session(self.engine) as db:
            for _ in range(count):
                lesson = Lesson(group_id=self.group_id)
                db.add(lesson)
                db.flush()
                db.add(Attendance(lesson_id=lesson.id, enrollment_id=self.enrollment_id, package_id=self.package_id))
            db.commit()

    def open_lesson(self):
        with Session(self.engine) as db:
            now = utc_now()
            db.add(Lesson(group_id=self.group_id, attendance_code="123456", started_at=now,
                          code_expires_at=now + timedelta(minutes=15)))
            db.commit()

    def test_early_renewal_keeps_unused_credit_and_queues_next_package(self):
        self.fill(8)
        self.renew()
        balance = self.balance()
        self.assertEqual((balance["available"], balance["queued"], balance["owed"]), (16, 12, 0))
        self.open_lesson()
        check_in(self.engine, self.student_id, "123456")
        self.assertEqual([p["used"] for p in self.balance()["packages"]], [9, 0])

    def test_late_renewal_settles_debt_without_rewriting_history(self):
        self.fill(14)
        with Session(self.engine) as db:
            before = db.execute(select(Attendance.id, Attendance.package_id, Attendance.checked_in_at)).all()
        self.assertEqual(self.balance()["owed"], 2)
        self.renew()
        balance = self.balance()
        self.assertEqual((balance["available"], balance["owed"]), (10, 0))
        self.assertEqual(balance["packages"][1]["carried_in"], 2)
        self.open_lesson()
        self.assertEqual(check_in(self.engine, self.student_id, "123456"), 9)
        with Session(self.engine) as db:
            after = db.execute(select(Attendance.id, Attendance.package_id, Attendance.checked_in_at)
                               .where(Attendance.id <= before[-1].id)).all()
        self.assertEqual(before, after)
        self.assertEqual(self.balance()["packages"][1]["remaining"], 9)

    def test_debt_larger_than_one_renewal_carries_forward(self):
        self.fill(26)
        self.renew()
        self.assertEqual((self.balance()["available"], self.balance()["owed"]), (0, 2))
        self.renew()
        self.assertEqual((self.balance()["available"], self.balance()["owed"]), (10, 0))

    def test_renewal_is_isolated_to_enrollment(self):
        self.fill(14)
        self.renew()
        other = self.balance(self.other_enrollment_id)
        self.assertEqual((other["included"], other["attended"], other["available"]), (12, 0, 12))

    def test_double_submission_and_new_attendance_reject_stale_preview(self):
        snapshot = self.balance()
        self.renew(snapshot)
        with self.assertRaisesRegex(ValueError, "balance changed"):
            self.renew(snapshot)
        newer = self.balance()
        self.fill(1)
        with self.assertRaisesRegex(ValueError, "balance changed"):
            self.renew(newer)
        self.assertEqual(self.balance()["included"], 24)

    def test_inactive_enrollment_and_student_actor_rejected(self):
        with self.assertRaisesRegex(ValueError, "Only a teacher"):
            renew_package(self.engine, self.student_id, self.enrollment_id, self.package_id, 0)
        with Session(self.engine) as db:
            db.get(Enrollment, self.enrollment_id).active = False
            db.commit()
        with self.assertRaisesRegex(ValueError, "active enrollment"):
            self.renew()

    def test_concurrent_renewal_adds_one_package(self):
        snapshot = self.balance()
        barrier = Barrier(2)

        def submit(_):
            barrier.wait(timeout=5)
            try:
                self.renew(snapshot)
                return "saved"
            except ValueError:
                return "stale"

        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertCountEqual(list(executor.map(submit, range(2))), ["saved", "stale"])
        self.assertEqual(self.balance()["included"], 24)

    def test_concurrent_checkin_and_renewal_preserve_balance(self):
        self.fill(12)
        self.open_lesson()
        snapshot = self.balance()
        barrier = Barrier(2)

        def renewal():
            barrier.wait(timeout=5)
            try:
                self.renew(snapshot)
                return True
            except ValueError:
                return False

        def attendance():
            barrier.wait(timeout=5)
            check_in(self.engine, self.student_id, "123456")

        with ThreadPoolExecutor(max_workers=2) as executor:
            renewing, checking = executor.submit(renewal), executor.submit(attendance)
            saved = renewing.result()
            checking.result()
        if not saved:
            self.renew()
        self.assertEqual((self.balance()["attended"], self.balance()["available"]), (13, 11))


class RenewalPageTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.engine = make_engine(str(Path(directory.name) / "test.db"))
        self.addCleanup(self.engine.dispose)
        self.client = self.enterContext(TestClient(create_app(self.engine, "test-secret")))
        with Session(self.engine) as db:
            hashed = password_hasher.hash("test-only passphrase")
            teacher = User(username="teacher", display_name="Teacher", role="teacher", password_hash=hashed)
            student = User(username="student", display_name="Madina", role="student", password_hash=hashed)
            group = Group(name="SAT")
            db.add_all([teacher, student, group])
            db.flush()
            self.student_id, self.group_id = student.id, group.id
            enrollment = Enrollment(student_id=student.id, group_id=group.id)
            db.add(enrollment)
            db.flush()
            self.enrollment_id = enrollment.id
            db.add(LessonPackage(enrollment_id=enrollment.id))
            db.commit()
        self.path = f"/teacher/enrollments/{self.enrollment_id}/renew"
        self.login("teacher")

    def field(self, page, name):
        return re.search(fr'name="{name}" value="([^"]*)"', page.text).group(1)

    def login(self, name):
        self.client.cookies.clear()
        csrf = self.field(self.client.get("/login"), "csrf")
        self.client.post("/login", data={"username": name, "password": "test-only passphrase", "csrf": csrf})

    def test_preview_confirmation_and_replay(self):
        page = self.client.get(self.path)
        self.assertIn("24 lessons available", page.text)
        self.assertIn("No payment is taken", page.text)
        fields = {name: self.field(page, name) for name in ("csrf", "expected_package_id", "expected_attended")}
        self.assertEqual(self.client.post(self.path, data=fields, follow_redirects=False).status_code, 303)
        repeated = self.client.post(self.path, data=fields)
        self.assertEqual(repeated.status_code, 400)
        self.assertIn("already recorded", repeated.text)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(LessonPackage)), 2)
        self.login("student")
        student_page = self.client.get("/student")
        self.assertIn("Lessons available", student_page.text)
        self.assertNotIn("Renew package", student_page.text)

    def test_access_csrf_and_invalid_snapshot_are_rejected(self):
        self.assertEqual(self.client.post(self.path).status_code, 403)
        csrf = self.field(self.client.get(self.path), "csrf")
        self.assertEqual(self.client.post(self.path, data={"csrf": csrf, "expected_package_id": "bad"}).status_code, 400)
        self.login("student")
        self.assertEqual(self.client.get(self.path).status_code, 403)
        self.assertEqual(self.client.post(self.path).status_code, 403)
        self.client.cookies.clear()
        self.assertEqual(self.client.get(self.path, follow_redirects=False).status_code, 303)

    def test_late_checkin_notice_and_renewal_preview(self):
        with Session(self.engine) as db:
            package = db.scalar(select(LessonPackage))
            for _ in range(12):
                lesson = Lesson(group_id=self.group_id)
                db.add(lesson)
                db.flush()
                db.add(Attendance(lesson_id=lesson.id, enrollment_id=self.enrollment_id, package_id=package.id))
            now = utc_now()
            db.add(Lesson(group_id=self.group_id, attendance_code="123456", started_at=now,
                          code_expires_at=now + timedelta(minutes=15)))
            db.commit()
        self.login("student")
        csrf = self.field(self.client.get("/student"), "csrf")
        page = self.client.post("/student/check-in", data={"csrf": csrf, "code": "123456"})
        self.assertIn("1 lesson(s) owed", page.text)
        self.login("teacher")
        preview = self.client.get(self.path)
        self.assertIn("11 lessons available", preview.text)
        self.assertIn("covers previously owed lessons first", preview.text)
