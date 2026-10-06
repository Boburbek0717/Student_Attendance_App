"""Public practice uses fictional questions and never saves course attempts."""
import re
import unittest
from unittest.mock import patch
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException
import test_question_practice as fixtures
from app.question_bank.models import Attempt, Bookmark, Question, Choice
from app.question_bank.public_practice import GuestLimiter


class PublicPracticeTests(unittest.TestCase):
    setUp = fixtures.QuestionPracticeTests.setUp
    login = fixtures.QuestionPracticeTests.login
    token = fixtures.QuestionPracticeTests.token
    values = fixtures.QuestionPracticeTests.values
    post = fixtures.QuestionPracticeTests.post
    create = fixtures.QuestionPracticeTests.create
    ready = fixtures.QuestionPracticeTests.ready

    def form(self, q, retry=False):
        page = self.client.get(f'/questions/{q}' + ('?retry=1' if retry else ''))
        self.assertEqual(page.status_code, 200)
        data = {name: re.search(fr'name="{name}" value="([^"]+)"',page.text)[1]
                for name in ('csrf','revision_id','retry_key')}
        with Session(self.engine) as db:
            data['choice_id'] = db.scalar(select(Choice.id).where(Choice.revision_id==int(data['revision_id'])).order_by(Choice.position))
        return page, data

    def test_guest_disclosure_retry_and_no_course_writes(self):
        q = self.ready(); self.client.cookies.clear()
        page, data = self.form(q)
        self.assertNotIn('Two pairs make four.',page.text)
        result = self.client.post(f'/questions/{q}/answer',data=data)
        self.assertNotIn('Correct answer:',result.text)
        self.assertIn('Try again',result.text)
        repeat = self.client.post(f'/questions/{q}/answer',data=data)
        self.assertNotIn('Correct answer:',repeat.text)
        _, data = self.form(q,True)
        result = self.client.post(f'/questions/{q}/answer',data=data)
        self.assertIn('Correct answer: B',result.text)
        self.assertIn('Two pairs make four.',result.text)
        self.assertNotIn('practice-explanation" open',result.text)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Attempt)),0)
            self.assertEqual(db.scalar(select(func.count()).select_from(Bookmark)),0)

    def test_public_browsing_hides_drafts_and_private_routes(self):
        hidden=self.create(stem='Unpublished confidential draft');q=self.ready();self.client.cookies.clear()
        page=self.client.get('/questions')
        self.assertEqual(page.status_code,200)
        self.assertIn(f'/questions/themes/{self.skill}',page.text)
        self.assertNotIn('Unpublished confidential draft',page.text)
        self.assertEqual(self.client.get(f'/questions/{hidden}').status_code,404)
        self.assertEqual(self.client.get('/questions/99999999999999999999').status_code,404)
        page=self.client.get(f'/questions/themes/{self.skill}')
        self.assertIn(f'/questions/{q}',page.text)
        for url in ('/teacher/questions','/student/assignments','/student'):
            self.assertEqual(self.client.get(url,follow_redirects=False).status_code,303)
        self.assertEqual(self.client.get('/questions/themes/1?page=0').status_code,400)

    def test_csrf_choices_stale_revision_and_withdrawal(self):
        q=self.ready();self.client.cookies.clear();_,data=self.form(q)
        url=f'/questions/{q}/answer'
        self.assertEqual(self.client.post(url,data=dict(data,csrf='bad')).status_code,403)
        self.assertEqual(self.client.post(url,data=dict(data,choice_id=2**70)).status_code,400)
        self.assertEqual(self.client.post(url,data=dict(data,revision_id=0)).status_code,400)
        with Session(self.engine) as db:
            db.get(Question,q).status='draft';db.commit()
        self.assertEqual(self.client.post(url,data=data).status_code,404)

    def test_enrolled_students_keep_saved_practice_routes(self):
        q=self.ready()
        response=self.client.get(f'/questions/{q}',follow_redirects=False)
        self.assertEqual(response.headers['location'],f'/student/questions/{q}')
        self.login('teacher')
        self.assertEqual(self.client.get(f'/questions/{q}').status_code,200)

    def test_request_limits_and_recovery(self):
        limiter=GuestLimiter()
        with patch('app.question_bank.public_practice.time.monotonic',return_value=10):
            for _ in range(30):limiter.check('fictional',True)
            with self.assertRaises(HTTPException) as error:limiter.check('fictional',True)
            self.assertEqual(error.exception.status_code,429)
            limiter.check('fictional',False)
        with patch('app.question_bank.public_practice.time.monotonic',return_value=71):limiter.check('fictional',True)
        self.client.app.state.guest_limiter.buckets[('testclient',False)] = (__import__('time').monotonic(),240)
        response=self.client.get('/questions')
        self.assertEqual(response.status_code,429)
        self.assertEqual(response.headers['Retry-After'],'60')
