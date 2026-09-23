from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import test_lesson_management as fixtures
from app.database import make_engine
from app.main import create_app
from app.models import LoginAttemptWindow, User
from app.security import limit_login_attempt, password_hasher


class ClassroomLoginTests(unittest.TestCase):
    setUp = fixtures.LessonManagementTests.setUp
    field = fixtures.LessonManagementTests.field
    login = fixtures.LessonManagementTests.login

    def test_thirty_students_and_teacher_from_same_ip(self):
        with Session(self.engine) as db:
            hashed = password_hasher.hash('test-only passphrase')
            db.add_all([User(username=f'class{i}', display_name=f'Demo {i}', role='student', password_hash=hashed) for i in range(30)])
            db.commit()
        with TestClient(self.app) as browser:
            for username in [*(f'class{i}' for i in range(30)), 'teacher']:
                browser.cookies.clear()
                token = self.field(browser.get('/login'), 'csrf')
                response = browser.post('/login', data={'username': username, 'password': 'test-only passphrase', 'csrf': token}, follow_redirects=False)
                self.assertEqual(response.status_code, 303, username)

    def test_account_limit_shared_across_ips_workers_and_restart(self):
        other = make_engine(self.engine.url.database)
        self.addCleanup(other.dispose)
        with patch('app.security.time', return_value=10000000000):
            for i in range(10):
                limit_login_attempt(self.engine, ' STUDENT ', f'peer{i}')
            with self.assertRaises(HTTPException) as error:
                limit_login_attempt(other, 'student', 'new-peer')
            self.assertEqual(error.exception.status_code, 429)
            with TestClient(create_app(other, 'test-secret')) as restarted:
                response = restarted.post('/login', data={'username': 'student', 'password': 'test-only passphrase', 'csrf': self.field(restarted.get('/login'), 'csrf')})
                self.assertEqual(response.status_code, 429)
        with patch('app.security.time', return_value=10000000060):
            limit_login_attempt(other, 'student', 'new-peer')

    def test_connection_limit_for_rotating_names(self):
        with patch('app.security.time', return_value=10000000000):
            for i in range(120):
                limit_login_attempt(self.engine, f'unknown{i}', 'shared-peer')
            with self.assertRaises(HTTPException) as error:
                limit_login_attempt(self.engine, 'freshname', 'shared-peer')
            self.assertEqual(error.exception.status_code, 429)
            limit_login_attempt(self.engine, 'fresh-other', 'another-peer')

    def test_parallel_attempts_reserve_exactly_ten(self):
        def attempt(i):
            try:
                limit_login_attempt(self.engine, 'same-account', f'peer{i}')
                return 'allowed'
            except HTTPException:
                return 'blocked'
        with patch('app.security.time', return_value=10000000000), ThreadPoolExecutor(max_workers=4) as pool:
            values = list(pool.map(attempt, range(15)))
        self.assertEqual(values.count('allowed'), 10)
        self.assertEqual(values.count('blocked'), 5)

    def test_unknown_key_storage_bounded_without_evicting_limits(self):
        with Session(self.engine) as db:
            db.query(LoginAttemptWindow).delete()
            db.add_all([LoginAttemptWindow(key=f'seed:{i}', timestamps=[10000000000], updated_at=10000000000) for i in range(8192)])
            db.commit()
        with patch('app.security.time', return_value=10000000000):
            with self.assertRaises(HTTPException):
                limit_login_attempt(self.engine, 'new-user', 'new-peer')
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(LoginAttemptWindow)), 8192)
        with patch('app.security.time', return_value=10000000060):
            limit_login_attempt(self.engine, 'new-user', 'new-peer')
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(LoginAttemptWindow)), 2)
