from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Barrier
import sqlite3
import tempfile
import unittest
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session
import test_lesson_management as fixtures
from app.attendance import check_in
from app.attendance_corrections import correct_attendance, correction_context
from app.database import initialize_database, make_engine
from app.lesson_management import close_permanently, closure_version
from app.models import Attendance, CheckInReceipt, Lesson, User
from app.packages import enrollment_balance


class LiveAttendanceTests(unittest.TestCase):
    setUp = fixtures.LessonManagementTests.setUp
    field = fixtures.LessonManagementTests.field
    login = fixtures.LessonManagementTests.login
    snapshot = fixtures.LessonManagementTests.snapshot

    def finish(self):
        with Session(self.engine) as db:
            version = closure_version(db, db.get(Lesson, self.lesson_id))
        close_permanently(self.engine, self.teacher_id, self.lesson_id, 'finished', 'Class complete', version)

    def test_lost_response_then_finish_and_retry(self):
        self.login('student')
        page = self.client.get('/student')
        data = {'csrf': self.field(page, 'csrf'), 'retry_key': self.field(page, 'retry_key'), 'code': self.snapshot()[0]}
        self.assertEqual(self.client.post('/student/check-in', data=data, follow_redirects=False).status_code, 303)
        self.finish()
        response = self.client.post('/student/check-in', data=data)
        self.assertIn('Already checked in. No extra lesson was used.', response.text)
        self.assertIn(f'SAT · Lesson #{self.lesson_id}', response.text)
        with Session(self.engine) as db:
            self.assertEqual(enrollment_balance(db, self.enrollment_id)['balance'], 11)
            self.assertEqual(db.scalar(select(func.count()).select_from(Attendance)), 1)

    def test_simultaneous_retries_have_one_debit(self):
        code = self.snapshot()[0]
        barrier = Barrier(2)
        def submit():
            barrier.wait()
            return check_in(self.engine, self.student_id, code, retry_key='a' * 32)
        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = pool.submit(submit), pool.submit(submit)
            self.assertEqual(sorted([a.result()['already'], b.result()['already']]), [False, True])
        with Session(self.engine) as db:
            self.assertEqual(enrollment_balance(db, self.enrollment_id)['balance'], 11)
            self.assertEqual(db.scalar(select(func.count()).select_from(CheckInReceipt)), 1)

    def test_receipt_cannot_restore_reversal_or_accept_different_code(self):
        code = self.snapshot()[0]
        check_in(self.engine, self.student_id, code, retry_key='a' * 32)
        other = '000000' if code != '000000' else '111111'
        with self.assertRaisesRegex(ValueError, 'different code'):
            check_in(self.engine, self.student_id, other, retry_key='a' * 32)
        with Session(self.engine) as db:
            version = correction_context(db, self.lesson_id, self.enrollment_id)['version']
        correct_attendance(self.engine, self.teacher_id, self.lesson_id, self.enrollment_id, 'reverse', 'Wrong attendance', version)
        with self.assertRaisesRegex(ValueError, 'reversed'):
            check_in(self.engine, self.student_id, code, retry_key='a' * 32)
        with Session(self.engine) as db:
            self.assertEqual(enrollment_balance(db, self.enrollment_id)['balance'], 12)

    def test_receipt_is_bound_to_student_and_session(self):
        code = self.snapshot()[0]
        check_in(self.engine, self.student_id, code, retry_key='a' * 32)
        self.finish()
        with Session(self.engine) as db:
            stranger = User(username='stranger', display_name='Stranger', role='student', password_hash='unused')
            db.add(stranger); db.commit(); stranger_id = stranger.id
        with self.assertRaisesRegex(ValueError, 'expired'):
            check_in(self.engine, stranger_id, code, retry_key='a' * 32)
        self.client.cookies.clear()
        self.assertEqual(self.client.post('/student/check-in', data={'code': code, 'retry_key': 'a' * 32}, follow_redirects=False).status_code, 303)

    def test_teacher_refresh_is_private_escaped_and_does_not_use_attempts(self):
        before = self.client.get(self.url)
        self.assertIn('id="lesson-live"', before.text)
        self.assertIn('Absent · 1', before.text)
        check_in(self.engine, self.student_id, self.snapshot()[0])
        after = self.client.get(self.url)
        self.assertIn('Present · 1', after.text)
        self.assertIn('&lt;script&gt;Student', after.text)
        self.assertEqual(after.headers['cache-control'], 'no-store')
        self.login('student')
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.cookies.clear()
        self.assertEqual(self.client.get(self.url, follow_redirects=False).status_code, 303)

    def test_rate_limit_is_readable_html_with_retry_after(self):
        self.login('student')
        page = self.client.get('/student')
        data = {'csrf': self.field(page, 'csrf'), 'retry_key': self.field(page, 'retry_key'), 'code': 'bad'}
        for _ in range(10):
            self.assertEqual(self.client.post('/student/check-in', data=data).status_code, 400)
        response = self.client.post('/student/check-in', data=data)
        self.assertEqual(response.status_code, 429)
        self.assertIn('Try again in', response.text)
        self.assertIn('text/html', response.headers['content-type'])
        self.assertTrue(1 <= int(response.headers['retry-after']) <= 60)

    def test_receipt_failure_rolls_back_attendance(self):
        def fail_receipt(connection, cursor, statement, parameters, context, many):
            if statement.startswith('INSERT INTO check_in_receipts'):
                raise RuntimeError('Simulated storage failure')
        event.listen(self.engine, 'before_cursor_execute', fail_receipt)
        try:
            with self.assertRaises(RuntimeError):
                check_in(self.engine, self.student_id, self.snapshot()[0], retry_key='a' * 32)
        finally:
            event.remove(self.engine, 'before_cursor_execute', fail_receipt)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Attendance)), 0)
            self.assertEqual(enrollment_balance(db, self.enrollment_id)['balance'], 12)

    def test_upgrade_and_backup_restore_receipt(self):
        # Additive migration recreates only the new empty table on an old schema.
        CheckInReceipt.__table__.drop(self.engine)
        initialize_database(self.engine)
        code = self.snapshot()[0]
        check_in(self.engine, self.student_id, code, retry_key='a' * 32)
        self.finish()
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'restored.db')
            with closing(sqlite3.connect(self.engine.url.database)) as source, closing(sqlite3.connect(path)) as target:
                source.backup(target)
            restored = make_engine(path)
            try:
                initialize_database(restored)
                self.assertTrue(check_in(restored, self.student_id, code, retry_key='a' * 32)['already'])
                with Session(restored) as db:
                    self.assertEqual(enrollment_balance(db, self.enrollment_id)['balance'], 11)
            finally:
                restored.dispose()
