from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import unittest

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

import test_attendance as fixtures
from app.database import make_engine
from app.main import create_app
from app.models import Attendance, AttendanceAttemptWindow, LoginSession
from app.security import limit_attendance_attempt


class AttendanceSecurityTests(unittest.TestCase):
    setUp = fixtures.AttendancePageTests.setUp
    login = fixtures.AttendancePageTests.login
    token = fixtures.AttendancePageTests.token
    start = fixtures.AttendancePageTests.start

    def test_limit_survives_app_restart_and_new_login(self):
        with patch('app.security.time', return_value=100):
            token = self.token(self.student.get('/student'))
            for _ in range(10):
                self.assertEqual(self.student.post('/student/check-in', data={'csrf': token, 'code': '999999'}).status_code, 400)
            with TestClient(create_app(self.engine, 'test-secret')) as restarted:
                self.login(restarted, 'student')
                response = restarted.post('/student/check-in', data={'csrf': self.token(restarted.get('/student')), 'code': '999999'})
                self.assertEqual(response.status_code, 429)
                self.assertEqual(response.headers['retry-after'], '60')
        with patch('app.security.time', return_value=160):
            response = self.student.post('/student/check-in', data={'csrf': token, 'code': '999999'})
            self.assertEqual(response.status_code, 400)
        with Session(self.engine) as db:
            self.assertEqual(db.get(AttendanceAttemptWindow, self.student_id).timestamps, [160])

    def test_parallel_workers_share_ten_attempt_budget(self):
        second_engine = make_engine(self.engine.url.database)
        self.addCleanup(second_engine.dispose)
        def attempt(index):
            try:
                limit_attendance_attempt(self.engine if index % 2 else second_engine, self.student_id)
                return 'allowed'
            except HTTPException as error:
                self.assertEqual(error.status_code, 429)
                return 'blocked'
        with patch('app.security.time', return_value=100), ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(attempt, range(16)))
        self.assertEqual(results.count('allowed'), 10)
        self.assertEqual(results.count('blocked'), 6)
        with Session(self.engine) as db:
            self.assertEqual(len(db.get(AttendanceAttemptWindow, self.student_id).timestamps), 10)

    def test_wrong_group_code_and_unknown_code_have_identical_response(self):
        code = self.start()
        self.student.cookies.clear()
        self.login(self.student, 'other')
        token = self.token(self.student.get('/student'))
        guessed = '999999' if code != '999999' else '888888'
        responses = [self.student.post('/student/check-in', data={'csrf': token, 'code': value, 'retry_key': 'r' * 32}) for value in (code, guessed)]
        self.assertEqual(responses[0].status_code, 400)
        self.assertEqual(responses[0].text, responses[1].text)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Attendance)), 0)

    def test_revoked_session_between_authorization_and_write_cannot_attend(self):
        code = self.start()
        token = self.token(self.student.get('/student'))
        def revoke_after_limit(engine, user_id):
            limit_attendance_attempt(engine, user_id)
            with Session(engine) as db:
                db.execute(delete(LoginSession).where(LoginSession.user_id == user_id))
                db.commit()
        with patch('app.student.limit_attendance_attempt', side_effect=revoke_after_limit):
            response = self.student.post('/student/check-in', data={'csrf': token, 'code': code}, follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers['location'], '/login')
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Attendance)), 0)

    def test_malformed_attempts_count_but_csrf_failure_does_not(self):
        token = self.token(self.student.get('/student'))
        self.assertEqual(self.student.post('/student/check-in', data={'code': '123456'}).status_code, 403)
        with Session(self.engine) as db:
            self.assertIsNone(db.get(AttendanceAttemptWindow, self.student_id))
        with patch('app.security.time', return_value=100):
            for _ in range(10):
                self.assertEqual(self.student.post('/student/check-in', data={'csrf': token, 'code': 'not-a-code'}).status_code, 400)
            response = self.student.post('/student/check-in', data={'csrf': token, 'code': '123456'})
            self.assertEqual(response.status_code, 429)
            # Another student has an independent allowance; shared classroom Wi-Fi
            # does not let one student block the entire group.
            limit_attendance_attempt(self.engine, self.other_id)
