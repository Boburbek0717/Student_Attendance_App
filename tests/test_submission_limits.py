"""Isolated persisted-budget and classroom HTTP regression checks."""
import secrets
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from app.database import make_engine, write_transaction
from app.models import User, Enrollment, Group, utc_now
from app.question_bank.models import Attempt, AssignmentAttempt, AssignmentRecipient
from app.question_bank.submission_limits import limit_new_answer
import test_assignments as assignment_fixtures
from test_question_authoring import PASSWORD


class SubmissionLimitTests(unittest.TestCase):
    for name in ('setUp', 'token', 'login', 'values', 'post', 'create', 'ready',
                 'answer_values', 'assigned', 'form'):
        locals()[name] = getattr(assignment_fixtures.AssignmentTests, name)

    def test_shared_persisted_limit_retry_and_expiry(self):
        q, aid, iid = self.assigned()  # Includes one independent practice attempt.
        url, data = self.form(aid, iid)
        for _ in range(29):
            data['retry_key'] = secrets.token_urlsafe(32)
            response = self.client.post(url + '/answer', data=data, follow_redirects=False)
            self.assertEqual(response.status_code, 303, response.text)
        # A lost-response retry still succeeds at capacity.
        self.assertEqual(self.client.post(url + '/answer', data=data, follow_redirects=False).status_code, 303)
        fresh = dict(data, retry_key=secrets.token_urlsafe(32))
        blocked = self.client.post(url + '/answer', data=fresh)
        self.assertEqual(blocked.status_code, 429)
        self.assertIn('This answer was not saved', blocked.text)
        self.assertIn(f'name="retry_key" value="{fresh["retry_key"]}"', blocked.text)
        self.assertRegex(blocked.text, rf'name="choice_id" value="{fresh["choice_id"]}" required checked')
        self.assertIn('id="answer-error"', blocked.text)
        self.assertNotIn('Correct answer:', blocked.text)
        self.assertTrue(1 <= int(blocked.headers['Retry-After']) <= 60)
        practice = dict(self.answer_values(q), retry_key=secrets.token_urlsafe(32))
        self.assertEqual(self.client.post(f'/student/questions/{q}/answer', data=practice).status_code, 429)
        with Session(self.engine) as db:
            uid = db.scalar(select(User.id).where(User.username == 'student'))
            self.assertEqual(db.scalar(select(func.count()).select_from(AssignmentAttempt)), 29)
        # A new engine has no in-memory limiter state to share.
        reopened = make_engine(self.engine.url.database)
        try:
            with self.assertRaises(HTTPException) as caught:
                with write_transaction(reopened) as db:
                    limit_new_answer(db, uid)
            self.assertEqual(caught.exception.status_code, 429)
        finally:
            reopened.dispose()
        with patch('app.question_bank.submission_limits.utc_now', return_value=utc_now() + timedelta(seconds=61)):
            self.assertEqual(self.client.post(url + '/answer', data=fresh, follow_redirects=False).status_code, 303)

    def test_concurrent_final_slot_is_atomic(self):
        q, aid, iid = self.assigned()
        url, data = self.form(aid, iid)
        for _ in range(28):
            self.assertEqual(self.client.post(url + '/answer', data=dict(data,
                retry_key=secrets.token_urlsafe(32)), follow_redirects=False).status_code, 303)
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: self.client.post(url + '/answer',
                data=dict(data, retry_key=secrets.token_urlsafe(32)), follow_redirects=False), range(2)))
        self.assertEqual(sorted(r.status_code for r in responses), [303, 429])
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(AssignmentAttempt)), 29)

    def test_thirty_students_submit_and_retry_on_shared_connection(self):
        q, aid, iid = self.assigned()
        url, template = self.form(aid, iid)
        with Session(self.engine) as db:
            original = db.scalar(select(User).where(User.username == 'student'))
            gid = db.scalar(select(Group.id))
            for i in range(30):
                student = User(username=f'classroom{i}', display_name=f'Fictional {i}',
                               role='student', password_hash=original.password_hash)
                db.add(student); db.flush()
                db.add(Enrollment(student_id=student.id, group_id=gid))
                db.add(AssignmentRecipient(assignment_id=aid, student_id=student.id))
            db.commit()
        clients = []
        for i in range(30):
            client = TestClient(self.client.app)
            self.addCleanup(client.close)
            login = client.get('/login')
            response = client.post('/login', data=dict(csrf=self.token(login),
                username=f'classroom{i}', password=PASSWORD), follow_redirects=False)
            self.assertEqual(response.status_code, 303)
            page = client.get(url)
            self.assertEqual(page.status_code, 200)
            clients.append((client, dict(template, csrf=self.token(page), retry_key=secrets.token_urlsafe(32))))
        def submit(pair):
            client, data = pair
            first = client.post(url + '/answer', data=data, follow_redirects=False)
            retry = client.post(url + '/answer', data=data, follow_redirects=False)
            return first.status_code, retry.status_code
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=30) as pool:
            outcomes = list(pool.map(submit, clients))
        elapsed = time.perf_counter() - started
        self.assertEqual(outcomes, [(303, 303)] * 30)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(AssignmentAttempt)), 30)
        print(f'Fictional classroom: 30 concurrent students, 60 POSTs including retries, {elapsed:.3f}s')
