from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Barrier
import re
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.attendance import check_in, start_lesson
from app.database import initialize_database, make_engine
from app.main import create_app
from app.models import Attendance, Enrollment, Group, Lesson, LessonPackage, User, utc_now
from app.security import password_hasher
from app.packages import package_balance, package_rows


class AttendanceRulesTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.engine = make_engine(str(Path(directory.name) / "test.db"))
        self.addCleanup(self.engine.dispose)
        initialize_database(self.engine)
        with Session(self.engine) as db:
            student = User(username="student", display_name="Student", role="student", password_hash="placeholder")
            teacher = User(username="teacher", display_name="Teacher", role="teacher", password_hash="placeholder")
            group, other = Group(name="SAT"), Group(name="IELTS")
            db.add_all([student, teacher, group, other])
            db.flush()
            self.student_id, self.teacher_id = student.id, teacher.id
            self.group_id, self.other_group_id = group.id, other.id
            enrollment = Enrollment(student_id=student.id, group_id=group.id)
            db.add(enrollment)
            db.flush()
            self.enrollment_id = enrollment.id
            package = LessonPackage(enrollment_id=enrollment.id)
            db.add(package)
            db.flush()
            self.package_id = package.id
            db.commit()

    def lesson(self, code="000123", group_id=None, minutes=15):
        with Session(self.engine) as db:
            now = utc_now()
            lesson = Lesson(group_id=group_id or self.group_id, attendance_code=code,
                            started_at=now, code_expires_at=now + timedelta(minutes=minutes))
            db.add(lesson)
            db.commit()
            return lesson.id

    def count(self):
        with Session(self.engine) as db:
            return db.scalar(select(func.count()).select_from(Attendance))

    def fill_package(self, count):
        with Session(self.engine) as db:
            for _ in range(count):
                lesson = Lesson(group_id=self.group_id)
                db.add(lesson)
                db.flush()
                db.add(Attendance(lesson_id=lesson.id, enrollment_id=self.enrollment_id, package_id=self.package_id))
            db.commit()

    def test_valid_code_records_one_lesson_and_duplicate_is_rejected(self):
        self.lesson()
        check_in(self.engine, self.student_id, " 000123 ")
        with self.assertRaisesRegex(ValueError, "already checked in"):
            check_in(self.engine, self.student_id, "000123")
        self.assertEqual(self.count(), 1)

    def test_expiry_boundary_and_unknown_code(self):
        lesson_id = self.lesson()
        with Session(self.engine) as db:
            expiry = db.get(Lesson, lesson_id).code_expires_at
        with patch("app.attendance.utc_now", return_value=expiry):
            with self.assertRaisesRegex(ValueError, "expired"):
                check_in(self.engine, self.student_id, "000123")
        with self.assertRaisesRegex(ValueError, "invalid"):
            check_in(self.engine, self.student_id, "999999")
        self.assertEqual(self.count(), 0)

    def test_wrong_group_and_inactive_membership(self):
        self.lesson(group_id=self.other_group_id)
        with self.assertRaisesRegex(ValueError, "active enrollment"):
            check_in(self.engine, self.student_id, "000123")
        self.lesson(code="000456")
        with Session(self.engine) as db:
            db.get(Enrollment, self.enrollment_id).active = False
            db.commit()
        with self.assertRaisesRegex(ValueError, "active enrollment"):
            check_in(self.engine, self.student_id, "000456")
        self.assertEqual(self.count(), 0)

    def test_missing_package_and_invalid_format(self):
        self.lesson()
        with Session(self.engine) as db:
            db.delete(db.get(LessonPackage, self.package_id))
            db.commit()
        for code in ("", "12345", "１２３４５６", "abcdef"):
            with self.assertRaisesRegex(ValueError, "six-digit"):
                check_in(self.engine, self.student_id, code)
        with self.assertRaisesRegex(ValueError, "no lesson package"):
            check_in(self.engine, self.student_id, "000123")
        self.assertEqual(self.count(), 0)

    def test_exhausted_package_records_lessons_owed(self):
        self.fill_package(12)
        self.lesson()
        self.assertEqual(check_in(self.engine, self.student_id, "000123"), -1)
        self.assertEqual(self.count(), 13)

    def test_oldest_available_package_and_history_preserved(self):
        with Session(self.engine) as db:
            renewal = LessonPackage(enrollment_id=self.enrollment_id)
            db.add(renewal)
            db.commit()
            renewal_id = renewal.id
        self.fill_package(11)
        first, second = self.lesson(), self.lesson(code="000456")
        check_in(self.engine, self.student_id, "000123")
        check_in(self.engine, self.student_id, "000456")
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(Attendance.package_id).where(Attendance.lesson_id == first)), self.package_id)
            self.assertEqual(db.scalar(select(Attendance.package_id).where(Attendance.lesson_id == second)), renewal_id)
        self.assertEqual(self.count(), 13)

    def test_start_reuses_open_lesson_and_honors_duration(self):
        first = start_lesson(self.engine, self.teacher_id, self.group_id, 10)
        second = start_lesson(self.engine, self.teacher_id, self.group_id, 10)
        self.assertEqual(first, second)
        with Session(self.engine) as db:
            lesson = db.get(Lesson, first)
            self.assertRegex(lesson.attendance_code, r"^[0-9]{6}$")
            self.assertEqual(lesson.code_expires_at - lesson.started_at, timedelta(minutes=10))

    def test_start_retries_code_collisions(self):
        self.lesson(group_id=self.other_group_id)
        with patch("app.attendance.secrets.randbelow", side_effect=[123, 456]):
            lesson_id = start_lesson(self.engine, self.teacher_id, self.group_id)
        with Session(self.engine) as db:
            self.assertEqual(db.get(Lesson, lesson_id).attendance_code, "000456")

    def test_only_teacher_starts_and_only_student_checks_in(self):
        with self.assertRaisesRegex(ValueError, "Only a teacher"):
            start_lesson(self.engine, self.student_id, self.group_id)
        self.lesson()
        with self.assertRaisesRegex(ValueError, "Only a student"):
            check_in(self.engine, self.teacher_id, "000123")

    def test_ambiguous_active_code_is_rejected_without_using_a_lesson(self):
        self.lesson()
        self.lesson(group_id=self.other_group_id)
        with self.assertRaisesRegex(ValueError, "invalid or has expired"):
            check_in(self.engine, self.student_id, "000123")
        self.assertEqual(self.count(), 0)

    def test_failed_attendance_write_rolls_back_and_can_be_retried(self):
        self.lesson()

        def fail(mapper, connection, target):
            raise IntegrityError("test insert failure", {}, Exception("forced failure"))

        event.listen(Attendance, "before_insert", fail)
        try:
            with self.assertRaisesRegex(ValueError, "could not be saved"):
                check_in(self.engine, self.student_id, "000123")
        finally:
            event.remove(Attendance, "before_insert", fail)
        self.assertEqual(self.count(), 0)
        check_in(self.engine, self.student_id, "000123")
        self.assertEqual(self.count(), 1)

    def test_database_lock_returns_retry_message_without_recording_attendance(self):
        self.lesson()
        contender = make_engine(self.engine.url.database)
        self.addCleanup(contender.dispose)

        @event.listens_for(contender, "connect")
        def short_timeout(connection, record):
            connection.execute("PRAGMA busy_timeout=1")

        with self.engine.connect() as holder:
            holder.exec_driver_sql("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(ValueError, "database is busy"):
                check_in(contender, self.student_id, "000123")
            holder.rollback()
        self.assertEqual(self.count(), 0)
        check_in(contender, self.student_id, "000123")
        self.assertEqual(self.count(), 1)

    def concurrent(self, actions):
        barrier = Barrier(len(actions))

        def run(action):
            barrier.wait(timeout=5)
            try:
                action()
                return "saved"
            except ValueError:
                return "rejected"

        with ThreadPoolExecutor(max_workers=len(actions)) as executor:
            return list(executor.map(run, actions))

    def test_concurrent_duplicate_saves_once(self):
        self.lesson()
        result = self.concurrent([lambda: check_in(self.engine, self.student_id, "000123")] * 2)
        self.assertCountEqual(result, ["saved", "rejected"])
        self.assertEqual(self.count(), 1)

    def test_concurrent_different_lessons_count_one_as_owed_after_credit_runs_out(self):
        self.fill_package(11)
        self.lesson()
        self.lesson(code="000456")
        result = self.concurrent([
            lambda: check_in(self.engine, self.student_id, "000123"),
            lambda: check_in(self.engine, self.student_id, "000456"),
        ])
        self.assertCountEqual(result, ["saved", "saved"])
        self.assertEqual(self.count(), 13)
        with Session(self.engine) as db:
            balance = package_balance(package_rows(db, self.enrollment_id))
            self.assertEqual((balance["available"], balance["owed"]), (0, 1))

    def test_concurrent_starts_create_one_lesson(self):
        result = self.concurrent([lambda: start_lesson(self.engine, self.teacher_id, self.group_id)] * 2)
        self.assertEqual(result, ["saved", "saved"])
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Lesson)), 1)


class AttendancePageTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.engine = make_engine(str(Path(directory.name) / "test.db"))
        self.addCleanup(self.engine.dispose)
        app = create_app(self.engine, "test-secret", code_minutes=10)
        self.teacher = self.enterContext(TestClient(app))
        self.student = self.enterContext(TestClient(app))
        self.app = app
        with Session(self.engine) as db:
            hashed = password_hasher.hash("test-only passphrase")
            teacher = User(username="teacher", display_name="Teacher", password_hash=hashed, role="teacher")
            student = User(username="student", display_name="Student", password_hash=hashed, role="student")
            other = User(username="other", display_name="Other Student", password_hash=hashed, role="student")
            group = Group(name="SAT Advanced")
            db.add_all([teacher, student, other, group])
            db.flush()
            self.group_id, self.student_id, self.other_id = group.id, student.id, other.id
            enrollment = Enrollment(student_id=student.id, group_id=group.id)
            db.add(enrollment)
            db.flush()
            db.add(LessonPackage(enrollment_id=enrollment.id))
            db.commit()
        self.login(self.teacher, "teacher")
        self.login(self.student, "student")

    def token(self, response):
        return re.search(r'name="csrf" value="([^"]+)"', response.text).group(1)

    def login(self, client, name):
        token = self.token(client.get("/login"))
        client.post("/login", data={"username": name, "password": "test-only passphrase", "csrf": token})

    def start(self):
        response = self.teacher.post(f"/teacher/groups/{self.group_id}/lessons",
                                     data={"csrf": self.token(self.teacher.get("/teacher"))}, follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        with Session(self.engine) as db:
            return db.scalar(select(Lesson.attendance_code))

    def test_full_flow_balances_and_teacher_history(self):
        code = self.start()
        self.assertIn(code, self.teacher.get("/teacher").text)
        self.assertNotIn(code, self.student.get("/student").text)
        response = self.student.post("/student/check-in", data={
            "csrf": self.token(self.student.get("/student")), "code": code, "student_id": self.other_id,
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        page = self.student.get("/student")
        self.assertIn("Attendance recorded", page.text)
        self.assertIn("1 / 12 lessons used", page.text)
        self.assertIn("11 remaining", page.text)
        self.assertIn("1 / 12 lessons used", self.teacher.get("/teacher").text)
        history = self.teacher.get(f"/teacher/students/{self.student_id}/history")
        self.assertIn("SAT Advanced", history.text)
        self.assertNotIn("No attendance recorded", history.text)
        with Session(self.engine) as db:
            owner = db.scalar(select(Enrollment.student_id).join(Attendance, Attendance.enrollment_id == Enrollment.id))
            self.assertEqual(owner, self.student_id)

    def test_routes_reject_wrong_role_and_missing_csrf(self):
        path = f"/teacher/groups/{self.group_id}/lessons"
        self.assertEqual(self.student.post(path).status_code, 403)
        self.assertEqual(self.teacher.post(path).status_code, 403)
        self.assertEqual(self.teacher.post("/student/check-in").status_code, 403)
        self.assertEqual(self.student.post("/student/check-in").status_code, 403)
        self.assertEqual(self.student.get(f"/teacher/students/{self.other_id}/history").status_code, 403)
        self.student.cookies.clear()
        self.assertEqual(self.student.post("/student/check-in", follow_redirects=False).status_code, 303)

    def test_bad_code_message_and_limit(self):
        token = self.token(self.student.get("/student"))
        with patch("app.security.monotonic", return_value=100):
            for _ in range(10):
                response = self.student.post("/student/check-in", data={"csrf": token, "code": "999999"})
                self.assertEqual(response.status_code, 400)
                self.assertIn("invalid or has expired", response.text)
            self.assertEqual(self.student.post("/student/check-in", data={"csrf": token, "code": "999999"}).status_code, 429)

    def test_students_cannot_read_another_students_records(self):
        code = self.start()
        self.student.post("/student/check-in", data={"csrf": self.token(self.student.get("/student")), "code": code})
        self.student.cookies.clear()
        self.login(self.student, "other")
        response = self.student.get(f"/student?student_id={self.student_id}")
        self.assertIn("No attendance recorded", response.text)
        self.assertNotIn("SAT Advanced", response.text)

    def test_duration_configuration_is_validated(self):
        for minutes in (0, 61):
            with self.assertRaises(ValueError):
                create_app(self.engine, "test", code_minutes=minutes)
