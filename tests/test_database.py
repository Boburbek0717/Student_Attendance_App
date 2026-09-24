import unittest

from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base, make_engine
from app.models import Attendance, Enrollment, Group, Lesson, LessonPackage, User


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.engine = make_engine(":memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.session.close)
        student = User(username="madina", display_name="Madina", password_hash="test-placeholder")
        group = Group(name="SAT Advanced")
        self.session.add_all([student, group])
        self.session.flush()
        self.enrollment = Enrollment(student_id=student.id, group_id=group.id)
        self.lesson = Lesson(group_id=group.id)
        self.session.add_all([self.enrollment, self.lesson])
        self.session.flush()
        self.package = LessonPackage(enrollment_id=self.enrollment.id)
        self.session.add(self.package)
        self.session.commit()

    def attendance(self, package_id=None):
        return Attendance(
            enrollment_id=self.enrollment.id,
            lesson_id=self.lesson.id,
            package_id=package_id or self.package.id,
        )

    def assert_rejected(self, row):
        self.session.add(row)
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_tables_and_foreign_keys(self):
        self.assertEqual(set(inspect(self.engine).get_table_names()), {
            "users", "groups", "enrollments", "lesson_packages", "lessons", "attendance", "login_sessions",
            "balance_adjustments", "lesson_roster_snapshots", "lesson_roster", "attendance_attempt_windows", "login_attempt_windows", "attendance_corrections", "lesson_closures", "check_in_receipts"
        })
        self.assertEqual(self.session.scalar(text("PRAGMA foreign_keys")), 1)
        self.assert_rejected(Lesson(group_id=999))

    def test_duplicate_enrollment(self):
        self.assert_rejected(Enrollment(
            student_id=self.enrollment.student_id, group_id=self.enrollment.group_id
        ))

    def test_duplicate_attendance_even_with_another_package(self):
        self.session.add(self.attendance())
        renewal = LessonPackage(enrollment_id=self.enrollment.id)
        self.session.add(renewal)
        self.session.commit()
        self.assert_rejected(self.attendance(renewal.id))

    def test_package_must_belong_to_enrollment(self):
        other = User(username="ali", display_name="Ali", password_hash="test-placeholder")
        self.session.add(other)
        self.session.flush()
        enrollment = Enrollment(student_id=other.id, group_id=self.enrollment.group_id)
        self.session.add(enrollment)
        self.session.flush()
        package = LessonPackage(enrollment_id=enrollment.id)
        self.session.add(package)
        self.session.commit()
        self.assert_rejected(self.attendance(package.id))

    def test_positive_package_size(self):
        for size in (0, -1):
            with self.subTest(size=size):
                self.assert_rejected(LessonPackage(enrollment_id=self.enrollment.id, lesson_limit=size))

    def test_renewal_preserves_history_and_balances(self):
        self.session.add(self.attendance())
        renewal = LessonPackage(enrollment_id=self.enrollment.id)
        self.session.add(renewal)
        self.session.commit()
        used = self.session.scalar(select(func.count()).select_from(Attendance).where(
            Attendance.package_id == self.package.id
        ))
        self.assertEqual(self.package.lesson_limit - used, 11)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Attendance).where(
            Attendance.package_id == renewal.id
        )), 0)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(LessonPackage)), 2)

    def test_cannot_delete_used_package(self):
        self.session.add(self.attendance())
        self.session.commit()
        with self.assertRaises(IntegrityError):
            self.session.execute(delete(LessonPackage).where(LessonPackage.id == self.package.id))
            self.session.commit()
        self.session.rollback()
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Attendance)), 1)

    def test_invalid_role_and_duplicate_username(self):
        self.assert_rejected(User(username="bad", display_name="Bad", password_hash="test", role="owner"))
        self.assert_rejected(User(username="madina", display_name="Duplicate", password_hash="test"))

    def test_code_requires_expiry(self):
        self.assert_rejected(Lesson(group_id=self.enrollment.group_id, attendance_code="123456"))


if __name__ == "__main__":
    unittest.main()
