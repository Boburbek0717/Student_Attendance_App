import re
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from scripts.portfolio_demo import portfolio_demo, DEMO_PASSWORD, seed
from app.models import User, Attendance, LessonClosure
from app.question_bank.models import Question, Assignment


class PortfolioDemoTests(unittest.TestCase):
    def setUp(self):
        self.context = portfolio_demo()
        self.app = self.context.__enter__()
        self.addCleanup(self.context.__exit__, None, None, None)
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def login(self, username):
        page = self.client.get('/login')
        csrf = re.search(r'name="csrf" value="([^"]+)"', page.text)[1]
        return self.client.post('/login', data=dict(username=username, password=DEMO_PASSWORD, csrf=csrf))

    def test_seed_integrity_and_both_dashboards(self):
        self.assertIn('Public demo password', self.client.get('/login').text)
        self.assertEqual(self.login('demo-student').status_code, 200)
        self.assertIn('Demo: three quick questions', self.client.get('/student/assignments').text)
        self.assertEqual(self.client.get('/teacher').status_code, 403)
        self.client.cookies.clear()
        self.assertEqual(self.login('demo-teacher').status_code, 200)
        self.assertIn('Demo SAT practice', self.client.get('/teacher').text)
        with Session(self.app.state.database_engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(User)), 7)
            self.assertEqual(db.scalar(select(func.count()).select_from(Question).where(Question.status=='published')), 3)
            self.assertEqual(db.scalar(select(func.count()).select_from(Assignment)), 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(Attendance)), 4)
            self.assertEqual(db.scalar(select(func.count()).select_from(LessonClosure)), 1)
            self.assertEqual(db.execute(text('PRAGMA foreign_key_check')).all(), [])
        with self.assertRaises(ValueError):
            seed(self.app.state.database_engine)

    def test_account_mutations_blocked_and_goal_still_works(self):
        self.login('demo-teacher')
        for path in ('profile', 'password', 'enrollments/1/status'):
            self.assertEqual(self.client.post('/teacher/students/2/'+path, data={}).status_code, 403)
        self.client.cookies.clear()
        page = self.login('demo-student')
        csrf = re.search(r'name="csrf" value="([^"]+)"', page.text)[1]
        self.assertEqual(self.client.post('/student/goal', data=dict(csrf=csrf, target_score='1400', version='0'), follow_redirects=False).status_code, 303)
        self.assertIn('1400', self.client.get('/student').text)
        self.assertEqual(self.client.post('/student/goal', data=dict(csrf='bad', target_score='1500', version='1')).status_code, 403)

    def test_restart_uses_new_storage_and_sessions(self):
        self.login('demo-student')
        old_path = self.app.state.database_engine.url.database
        with portfolio_demo() as fresh:
            self.assertNotEqual(old_path, fresh.state.database_engine.url.database)
            with TestClient(fresh) as client:
                client.cookies.update(self.client.cookies)
                self.assertEqual(client.get('/student', follow_redirects=False).status_code, 303)
                self.assertIn('Portfolio demo', client.get('/login').text)
