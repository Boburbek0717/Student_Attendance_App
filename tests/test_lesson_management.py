from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Barrier
import re
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from app.attendance import check_in, start_lesson
from app.database import make_engine
from app.lesson_management import change_check_in, code_version
from app.main import create_app
from app.models import Attendance, Enrollment, Group, Lesson, LessonPackage, User, utc_now
from app.security import password_hasher


class LessonManagementTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.engine = make_engine(str(Path(directory.name) / 'test.db'))
        self.addCleanup(self.engine.dispose)
        self.app = create_app(self.engine, 'test-secret')
        self.client = self.enterContext(TestClient(self.app))
        with Session(self.engine) as db:
            hashed = password_hasher.hash('test-only passphrase')
            teacher = User(username='teacher', display_name='Teacher', role='teacher', password_hash=hashed)
            student = User(username='student', display_name='<script>Student</script>', role='student', password_hash=hashed)
            group = Group(name='SAT')
            db.add_all([teacher, student, group])
            db.flush()
            self.teacher_id, self.student_id, self.group_id = teacher.id, student.id, group.id
            membership = Enrollment(student_id=student.id, group_id=group.id)
            db.add(membership)
            db.flush()
            self.enrollment_id = membership.id
            db.add(LessonPackage(enrollment_id=membership.id))
            db.commit()
        self.lesson_id = start_lesson(self.engine, self.teacher_id, self.group_id)
        self.url = f'/teacher/lessons/{self.lesson_id}'
        self.history = f'/teacher/groups/{self.group_id}/lessons'
        self.login('teacher')

    def field(self, page, name):
        return re.search(fr'name="{name}" value="([^"]*)"', page.text).group(1)

    def login(self, username):
        self.client.cookies.clear()
        self.client.post('/login', data={'username': username, 'password': 'test-only passphrase',
                                        'csrf': self.field(self.client.get('/login'), 'csrf')})

    def snapshot(self):
        with Session(self.engine) as db:
            lesson = db.get(Lesson, self.lesson_id)
            return lesson.attendance_code, code_version(lesson), lesson.started_at

    def submit(self, action, version=None):
        page = self.client.get(self.url)
        return self.client.post(self.url + '/' + action, data={
            'csrf': self.field(page, 'csrf'),
            'expected_version': self.field(page, 'expected_version') if version is None else version,
        }, follow_redirects=False)

    def test_history_detail_and_group_isolation(self):
        self.assertIn('0 checked in', self.client.get(self.history).text)
        self.assertIn('Check-in open', self.client.get(self.url).text)
        self.assertIn('&lt;script&gt;', self.client.get(self.url).text)
        self.assertNotIn('<script>Student', self.client.get(self.url).text)
        check_in(self.engine, self.student_id, self.snapshot()[0])
        with Session(self.engine) as db:
            db.get(Enrollment, self.enrollment_id).active = False
            other = Group(name='Other')
            db.add(other)
            db.flush()
            other_id = other.id
            db.commit()
        self.assertIn('1 checked in', self.client.get(self.history).text)
        self.assertIn('Checked in · 1', self.client.get(self.url).text)
        self.assertIn('without a check-in · 0', self.client.get(self.url).text)
        self.assertIn('No lessons yet', self.client.get(f'/teacher/groups/{other_id}/lessons').text)

    def test_close_is_repeatable_preserves_records_and_rejects_code(self):
        code, version, started = self.snapshot()
        check_in(self.engine, self.student_id, code)
        for _ in range(2):
            self.assertEqual(self.submit('close', version).status_code, 303)
        with Session(self.engine) as db:
            lesson = db.get(Lesson, self.lesson_id)
            self.assertIsNone(lesson.attendance_code)
            self.assertIsNone(lesson.code_expires_at)
            self.assertEqual(lesson.started_at, started)
            self.assertEqual(db.scalar(select(func.count()).select_from(Attendance)), 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(LessonPackage)), 1)
        with self.assertRaisesRegex(ValueError, 'invalid or has expired'):
            check_in(self.engine, self.student_id, code)
        self.assertIn('Check-in closed', self.client.get(self.url).text)
        self.assertNotEqual(start_lesson(self.engine, self.teacher_id, self.group_id), self.lesson_id)

    def test_reopen_preserves_lesson_and_prevents_double_charge(self):
        old_code, old_version, started = self.snapshot()
        check_in(self.engine, self.student_id, old_code)
        self.submit('close')
        closed_version = self.snapshot()[1]
        self.assertEqual(self.submit('reopen', closed_version).status_code, 303)
        code, version, current_start = self.snapshot()
        self.assertEqual(current_start, started)
        self.assertEqual(self.submit('reopen', closed_version).status_code, 400)
        self.assertEqual(self.submit('close', old_version).status_code, 400)
        self.assertEqual(self.snapshot()[1], version)
        with self.assertRaisesRegex(ValueError, 'already checked in'):
            check_in(self.engine, self.student_id, code)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Attendance)), 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(Lesson)), 1)

    def test_expired_reopen_changes_code_and_accepts_late_student(self):
        with Session(self.engine) as db:
            lesson = db.get(Lesson, self.lesson_id)
            lesson.started_at = utc_now() - timedelta(hours=1)
            lesson.code_expires_at = utc_now() - timedelta(minutes=1)
            db.commit()
        old_code = self.snapshot()[0]
        self.assertIn('Check-in closed', self.client.get(self.url).text)
        self.assertNotIn('class="code"', self.client.get(self.url).text)
        self.assertEqual(self.submit('reopen').status_code, 303)
        code = self.snapshot()[0]
        self.assertNotEqual(code, old_code)
        self.assertEqual(check_in(self.engine, self.student_id, code), 11)
        with self.assertRaisesRegex(ValueError, 'invalid or has expired'):
            check_in(self.engine, self.student_id, old_code)

    def test_reopen_blocks_conflicting_lesson(self):
        self.submit('close')
        start_lesson(self.engine, self.teacher_id, self.group_id)
        result = self.submit('reopen')
        self.assertEqual(result.status_code, 400)
        self.assertIn('already has open check-in', result.text)
        self.assertIsNone(self.snapshot()[0])

    def test_permissions_csrf_and_invalid_ids(self):
        for action in ('close', 'reopen'):
            self.assertEqual(self.client.post(self.url + '/' + action).status_code, 403)
            self.assertEqual(self.client.get(self.url + '/' + action).status_code, 405)
        for record_id in (0, -1, 999, 2**80):
            self.assertEqual(self.client.get(f'/teacher/lessons/{record_id}').status_code, 404)
            self.assertEqual(self.client.get(f'/teacher/groups/{record_id}/lessons').status_code, 404)
            for action in ('close', 'reopen'):
                self.assertEqual(self.client.post(f'/teacher/lessons/{record_id}/{action}', data={
                    'csrf': self.field(self.client.get(self.url), 'csrf')}).status_code, 404)
        self.login('student')
        for path in (self.url, self.history):
            self.assertEqual(self.client.get(path).status_code, 403)
        for action in ('close', 'reopen'):
            self.assertEqual(self.client.post(self.url + '/' + action, data={
                'csrf': self.field(self.client.get('/student'), 'csrf')}).status_code, 403)
        with self.assertRaises(HTTPException) as error:
            change_check_in(self.engine, self.student_id, self.lesson_id, self.snapshot()[1])
        self.assertEqual(error.exception.status_code, 403)
        self.assertIsNotNone(self.snapshot()[0])
        self.client.cookies.clear()
        self.assertEqual(self.client.get(self.url, follow_redirects=False).status_code, 303)

    def test_history_pagination(self):
        with Session(self.engine) as db:
            for _ in range(25):
                db.add(Lesson(group_id=self.group_id))
            db.commit()
        self.assertIn('Page 1 of 2', self.client.get(self.history).text)
        self.assertIn('Page 2 of 2', self.client.get(self.history + '?page=999999999999999999999999999999').text)
        self.assertIn('Page 1 of 2', self.client.get(self.history + '?page=-1').text)

    def test_reopen_collision_failure_rolls_back(self):
        self.submit('close')
        with Session(self.engine) as db:
            group = Group(name='Other')
            db.add(group)
            db.flush()
            now = utc_now()
            db.add(Lesson(group_id=group.id, attendance_code='000123', started_at=now,
                          code_expires_at=now + timedelta(minutes=15)))
            db.commit()
        with patch('app.attendance.secrets.randbelow', return_value=123):
            self.assertEqual(self.submit('reopen').status_code, 400)
        self.assertIsNone(self.snapshot()[0])

    def test_simultaneous_reopens_do_not_rotate_twice(self):
        self.submit('close')
        version = self.snapshot()[1]
        ready = Barrier(2)
        def reopen():
            ready.wait(timeout=10)
            try:
                change_check_in(self.engine, self.teacher_id, self.lesson_id, version, reopen=True)
                return 'saved'
            except ValueError:
                return 'stale'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: reopen(), range(2)))
        self.assertCountEqual(results, ['saved', 'stale'])
        self.assertIsNotNone(self.snapshot()[0])

    def test_close_and_checkin_are_serialized(self):
        code, version, _ = self.snapshot()
        ready = Barrier(2)
        def close():
            ready.wait(timeout=10)
            change_check_in(self.engine, self.teacher_id, self.lesson_id, version)
        def attend():
            ready.wait(timeout=10)
            try:
                check_in(self.engine, self.student_id, code)
                return 1
            except ValueError:
                return 0
        with ThreadPoolExecutor(max_workers=2) as pool:
            closing = pool.submit(close)
            attending = pool.submit(attend)
            closing.result()
            expected = attending.result()
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Attendance)), expected)
            self.assertIsNone(db.get(Lesson, self.lesson_id).attendance_code)
        with self.assertRaises(ValueError):
            check_in(self.engine, self.student_id, code)

    def test_start_and_reopen_allow_only_one_open_lesson_in_group(self):
        self.submit('close')
        version = self.snapshot()[1]
        ready = Barrier(2)
        def reopen():
            ready.wait(timeout=10)
            try:
                change_check_in(self.engine, self.teacher_id, self.lesson_id, version, reopen=True)
            except ValueError:
                pass  # Starting the new lesson won the writer slot.
        def start():
            ready.wait(timeout=10)
            return start_lesson(self.engine, self.teacher_id, self.group_id)
        with ThreadPoolExecutor(max_workers=2) as pool:
            reopening, starting = pool.submit(reopen), pool.submit(start)
            reopening.result()
            lesson_id = starting.result()
        with Session(self.engine) as db:
            active = db.scalars(select(Lesson.id).where(
                Lesson.group_id == self.group_id, Lesson.code_expires_at > utc_now(),
            )).all()
            self.assertEqual(active, [lesson_id])
