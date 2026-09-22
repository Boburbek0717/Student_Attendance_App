from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import unittest

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import test_lesson_management as fixtures
from app.attendance import check_in, start_lesson
from app.database import initialize_database
from app.models import Attendance, BalanceAdjustment, Enrollment, Lesson, LessonPackage, LessonRoster, LessonRosterSnapshot, User
from app.packages import balance_version, enrollment_balance, renew_package, set_balance


class TeacherConvenienceTests(unittest.TestCase):
    setUp = fixtures.LessonManagementTests.setUp
    field = fixtures.LessonManagementTests.field
    login = fixtures.LessonManagementTests.login
    snapshot = fixtures.LessonManagementTests.snapshot

    def balance(self):
        with Session(self.engine) as db:
            return enrollment_balance(db, self.enrollment_id)

    def adjust(self, target, version=None, reason='Missed credit correction'):
        set_balance(self.engine, self.teacher_id, self.student_id, self.enrollment_id,
                    target, reason, version or balance_version(self.balance()))

    def test_balance_set_up_down_negative_zero_preserves_history(self):
        check_in(self.engine, self.student_id, self.snapshot()[0])
        for target in (20, 4, -3, 0):
            self.adjust(target)
            balance = self.balance()
            self.assertEqual(balance['balance'], target)
            self.assertEqual(sum(p['remaining'] for p in balance['packages']), max(0, target))
        with Session(self.engine) as db:
            changes = db.scalars(select(BalanceAdjustment).order_by(BalanceAdjustment.id)).all()
            self.assertEqual([(c.old_balance, c.new_balance) for c in changes], [(11,20),(20,4),(4,-3),(-3,0)])
            self.assertTrue(all(c.teacher_id == self.teacher_id and c.reason for c in changes))
            self.assertEqual(db.scalar(select(func.count()).select_from(Attendance)), 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(LessonPackage)), 1)

    def test_adjustment_checkin_and_renewal_use_same_balance(self):
        self.adjust(5)
        self.assertEqual(check_in(self.engine, self.student_id, self.snapshot()[0]), 4)
        b = self.balance()
        renew_package(self.engine, self.teacher_id, self.enrollment_id,
                      b['latest_package_id'], b['attended'], b['latest_adjustment_id'])
        self.assertEqual(self.balance()['balance'], 16)
        self.assertEqual(sum(p['remaining'] for p in self.balance()['packages']), 16)
        self.adjust(-2)
        b = self.balance()
        renew_package(self.engine, self.teacher_id, self.enrollment_id,
                      b['latest_package_id'], b['attended'], b['latest_adjustment_id'])
        self.assertEqual(self.balance()['balance'], 10)

    def test_stale_adjustment_and_renewal_are_rejected(self):
        original = self.balance()
        version = balance_version(original)
        self.adjust(7, version)
        with self.assertRaisesRegex(ValueError, 'balance changed'):
            self.adjust(6, version)
        with self.assertRaisesRegex(ValueError, 'balance changed'):
            renew_package(self.engine, self.teacher_id, self.enrollment_id,
                          original['latest_package_id'], original['attended'])
        version = balance_version(self.balance())
        check_in(self.engine, self.student_id, self.snapshot()[0])
        with self.assertRaisesRegex(ValueError, 'balance changed'):
            self.adjust(100, version)
        self.assertEqual(self.balance()['balance'], 6)

    def test_adjustment_validation_and_noop(self):
        for target, reason in ((1000001, 'Reason'), (-1000001, 'Reason'), (1, ' '), (1, 'x' * 501)):
            with self.assertRaises(ValueError):
                self.adjust(target, reason=reason)
        self.adjust(12)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(BalanceAdjustment)), 0)
        with self.assertRaises(ValueError):
            set_balance(self.engine, self.student_id, self.student_id, self.enrollment_id, 0, 'test', balance_version(self.balance()))
        with self.assertRaises(ValueError):
            set_balance(self.engine, self.teacher_id, self.student_id + 99, self.enrollment_id, 0, 'test', balance_version(self.balance()))
        with self.assertRaises(ValueError):
            set_balance(self.engine, self.teacher_id, self.student_id, 2**80, 0, 'test', balance_version(self.balance()))

    def test_teacher_form_student_display_and_permissions(self):
        path = f'/teacher/students/{self.student_id}/manage'
        action = f'/teacher/students/{self.student_id}/enrollments/{self.enrollment_id}/balance'
        page = self.client.get(path)
        data = {'csrf': self.field(page, 'csrf'), 'expected_version': self.field(page, 'expected_version'),
                'target': '8', 'reason': '<script>correction</script>'}
        self.assertEqual(self.client.post(action, data=data, follow_redirects=False).status_code, 303)
        page = self.client.get(path)
        self.assertIn('&lt;script&gt;correction&lt;/script&gt;', page.text)
        self.assertIn('Teacher corrections: -4 lessons', self.client.get('/teacher').text)
        self.assertEqual(self.client.post(action).status_code, 403)
        self.assertEqual(self.client.get(action).status_code, 405)
        data['expected_version'] = self.field(page, 'expected_version')
        data['target'] = '1.5'
        self.assertEqual(self.client.post(action, data=data).status_code, 400)
        self.login('student')
        page = self.client.get('/student')
        self.assertIn('Teacher corrections: -4 lessons', page.text)
        data['csrf'] = self.field(page, 'csrf')
        self.assertEqual(self.client.post(action, data=data).status_code, 403)
        self.assertEqual(self.balance()['balance'], 8)

    def test_absence_snapshot_survives_membership_changes_and_reopening(self):
        self.assertIn('Absent · 1', self.client.get(self.url).text)
        with Session(self.engine) as db:
            db.get(Enrollment, self.enrollment_id).active = False
            newcomer = User(username='new', display_name='New student', role='student', password_hash='placeholder')
            db.add(newcomer)
            db.flush()
            db.add(Enrollment(student_id=newcomer.id, group_id=self.group_id))
            db.commit()
        page = self.client.get(self.url)
        self.assertIn('Absent · 1', page.text)
        self.assertNotIn('New student', page.text)
        self.assertNotIn('no saved roster', page.text)
        with Session(self.engine) as db:
            db.get(Enrollment, self.enrollment_id).active = True
            db.commit()
        check_in(self.engine, self.student_id, self.snapshot()[0])
        page = self.client.get(self.url)
        self.assertIn('Present · 1', page.text)
        self.assertIn('Absent · 0', page.text)
        self.assertEqual(self.balance()['balance'], 11)

    def test_legacy_lesson_and_empty_roster_are_distinguished(self):
        with Session(self.engine) as db:
            legacy = Lesson(group_id=self.group_id)
            db.add(legacy)
            db.flush()
            legacy_id = legacy.id
            db.get(Enrollment, self.enrollment_id).active = False
            db.get(Lesson, self.lesson_id).attendance_code = None
            db.get(Lesson, self.lesson_id).code_expires_at = None
            db.commit()
        empty_id = start_lesson(self.engine, self.teacher_id, self.group_id)
        with Session(self.engine) as db:
            db.get(Enrollment, self.enrollment_id).active = True
            db.commit()
        self.assertIn('no saved roster', self.client.get(f'/teacher/lessons/{legacy_id}').text)
        page = self.client.get(f'/teacher/lessons/{empty_id}')
        self.assertIn('Absent · 0', page.text)
        self.assertNotIn('no saved roster', page.text)
        initialize_database(self.engine)
        initialize_database(self.engine)
        self.assertEqual(self.balance()['balance'], 12)

    def test_simultaneous_adjustments_save_once(self):
        version = balance_version(self.balance())
        ready = Barrier(2)
        def save(target):
            ready.wait(timeout=10)
            try:
                self.adjust(target, version)
                return 'saved'
            except ValueError:
                return 'stale'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(save, [4, 7]))
        self.assertCountEqual(results, ['saved', 'stale'])
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(BalanceAdjustment)), 1)

    def test_corrections_after_later_package_debt_keep_credit_consistent(self):
        b = self.balance()
        later_id = renew_package(self.engine, self.teacher_id, self.enrollment_id,
                                 b['latest_package_id'], b['attended'])
        self.adjust(12)
        # The deduction removes earlier credit; later attendance belongs to the
        # second package, even though the first purchase still exists in history.
        with Session(self.engine) as db:
            for _ in range(13):
                lesson = Lesson(group_id=self.group_id)
                db.add(lesson)
                db.flush()
                db.add(Attendance(lesson_id=lesson.id, enrollment_id=self.enrollment_id, package_id=later_id))
            db.commit()
        self.assertEqual(self.balance()['balance'], -1)
        self.adjust(4)
        b = self.balance()
        self.assertEqual(b['balance'], 4)
        self.assertEqual(sum(p['remaining'] for p in b['packages']), 4)
        self.assertEqual(check_in(self.engine, self.student_id, self.snapshot()[0]), 3)
        self.assertEqual(sum(p['remaining'] for p in self.balance()['packages']), 3)
