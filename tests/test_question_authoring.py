from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import select, func, delete
from sqlalchemy.orm import Session

from app.create_user import create_user
from app.database import make_engine
from app.main import create_app
from app.models import LoginSession
from app.question_bank.models import Question, Revision, Choice, AnswerKey, Source, Skill
from app.question_bank.authoring import save_draft

PASSWORD = 'fictional question test password'


class QuestionAuthoringTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.engine = make_engine(str(Path(directory.name) / 'fictional.db'))
        self.addCleanup(self.engine.dispose)
        self.client = self.enterContext(TestClient(create_app(self.engine, 'fictional-only-secret')))
        with Session(self.engine) as db:
            create_user(db, 'teacher', 'Fictional Teacher', PASSWORD, 'teacher')
            create_user(db, 'student', 'Fictional Student', PASSWORD, 'student')
            self.skill = db.scalar(select(Skill.id).order_by(Skill.id))
        self.login('teacher')

    def token(self, response):
        return re.search(r'name="csrf" value="([^"]+)"', response.text).group(1)

    def login(self, username):
        self.client.cookies.clear()
        self.client.post('/login', data={'csrf':self.token(self.client.get('/login')),
            'username':username, 'password':PASSWORD})

    def values(self, **updates):
        values = dict(skill_id=str(self.skill), difficulty='easy', stem='What is 2 + 2?',
            passage='A fictional passage.', choice_0='3', choice_1='4', answer='1',
            explanation='Two pairs make four.', source_name='Original', rights_note='Written for tests.')
        values.update(updates)
        return values

    def post(self, path='/teacher/questions/new', **updates):
        return self.client.post(path, data=dict(self.values(**updates),
            csrf=self.token(self.client.get('/teacher/questions/new'))), follow_redirects=False)

    def create(self, **updates):
        response = self.post(**updates)
        self.assertEqual(response.status_code, 303, response.text)
        return int(response.headers['location'].split('/')[3])

    def test_create_edit_and_historical_preview_preserve_content(self):
        question_id = self.create()
        with Session(self.engine) as db:
            original = db.get(Question, question_id).current_revision_id
            self.assertTrue(db.get(Revision, original).sealed)
        response = self.post(f'/teacher/questions/{question_id}/edit',
            expected_revision=str(original), stem='Updated question')
        self.assertEqual(response.status_code, 303)
        old = self.client.get(f'/teacher/questions/{question_id}/preview?revision_id={original}')
        self.assertIn('What is 2 + 2?', old.text)
        self.assertIn('Historical revision', old.text)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Revision)), 2)
            self.assertEqual(db.get(Question, question_id).status, 'draft')
        latest = self.client.get(f'/teacher/questions/{question_id}/preview')
        self.assertIn('Updated question', latest.text)
        self.assertIn('Correct answer: B', latest.text)
        self.assertIn('Written for tests.', latest.text)

    def test_incomplete_draft_and_validation_preserve_input(self):
        q = self.create(answer='', choice_0='', choice_1='', explanation='')
        self.assertIn('Correct answer not chosen', self.client.get(f'/teacher/questions/{q}/preview').text)
        for changes in [dict(stem=''), dict(skill_id='999999'), dict(difficulty='invalid'),
                        dict(choice_1=''), dict(source_name=''), dict(stem='a'*2001)]:
            response = self.post(**changes)
            self.assertEqual(response.status_code, 400)
            self.assertIn('Draft not saved', response.text)
            self.assertIn('Written for tests.', response.text)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Question)), 1)

    def test_stale_edit_does_not_overwrite_and_noop_adds_no_revision(self):
        q = self.create()
        with Session(self.engine) as db: original = db.get(Question, q).current_revision_id
        self.assertEqual(self.post(f'/teacher/questions/{q}/edit', expected_revision=str(original)).status_code, 303)
        self.assertEqual(self.post(f'/teacher/questions/{q}/edit', expected_revision=str(original), stem='First edit').status_code, 303)
        response = self.post(f'/teacher/questions/{q}/edit', expected_revision=str(original), stem='Second edit')
        self.assertEqual(response.status_code, 400)
        self.assertIn('A newer revision', response.text)
        self.assertIn('Second edit', response.text)
        self.assertIn(f'name="expected_revision" value="{original}"', response.text)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Revision)), 2)

    def test_routes_require_teacher_and_posts_require_csrf(self):
        q = self.create()
        for path in ['/teacher/questions/new', f'/teacher/questions/{q}/edit']:
            self.assertEqual(self.client.post(path, data=self.values()).status_code, 403)
        self.login('student')
        for path in ['/teacher/questions', '/teacher/questions/new', f'/teacher/questions/{q}/edit', f'/teacher/questions/{q}/preview']:
            self.assertEqual(self.client.get(path).status_code, 403)
        for path in ['/teacher/questions/new', f'/teacher/questions/{q}/edit']:
            self.assertEqual(self.client.post(path, data=self.values()).status_code, 403)
        self.client.cookies.clear()
        self.assertEqual(self.client.get('/teacher/questions', follow_redirects=False).headers['location'], '/login')

    def test_revoked_session_between_route_and_write_cannot_save(self):
        def revoked(*args, **kwargs):
            with self.engine.begin() as db: db.execute(delete(LoginSession))
            return save_draft(*args, **kwargs)
        with patch('app.question_bank.routes.save_draft', side_effect=revoked):
            self.assertEqual(self.post().headers['location'], '/login')
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Question)), 0)

    def test_cross_question_revision_and_large_ids_are_not_exposed(self):
        q1 = self.create(); q2 = self.create(stem='Other question')
        with Session(self.engine) as db: r = db.get(Question, q2).current_revision_id
        self.assertEqual(self.client.get(f'/teacher/questions/{q1}/preview?revision_id={r}').status_code, 404)
        self.assertEqual(self.client.get('/teacher/questions/999999999999999999999/preview').status_code, 404)
        self.assertEqual(self.client.get('/teacher/questions?page=999999999999999999999').status_code, 400)

    def test_html_escaped_and_duplicate_warning(self):
        q = self.create(stem='<script>alert(1)</script>', passage='<script>alert(1)</script>')
        other = self.create(stem='<script>alert(1)</script>', passage='<script>alert(1)</script>')
        for path in ['/teacher/questions', f'/teacher/questions/{q}/edit', f'/teacher/questions/{q}/preview']:
            page = self.client.get(path)
            self.assertNotIn('<script>alert(1)</script>', page.text)
            self.assertIn('&lt;script&gt;', page.text)
            self.assertEqual(page.headers['cache-control'], 'no-store')
        self.assertIn(f'question #{other}', self.client.get(f'/teacher/questions/{q}/preview').text)

    def test_failed_choice_write_rolls_back_question_revision_and_source(self):
        with patch('app.question_bank.authoring.Choice', side_effect=ValueError('Simulated write failure')):
            self.assertEqual(self.post().status_code, 400)
        with Session(self.engine) as db:
            for model in (Question, Revision, Choice, AnswerKey, Source):
                self.assertEqual(db.scalar(select(func.count()).select_from(model)), 0)

    def test_concurrent_edits_save_only_one_new_revision(self):
        q = self.create()
        with Session(self.engine) as db: original = db.get(Question, q).current_revision_id
        csrf = self.token(self.client.get('/teacher/questions/new'))
        def submit(stem):
            return self.client.post(f'/teacher/questions/{q}/edit', data=dict(
                self.values(stem=stem), expected_revision=str(original), csrf=csrf), follow_redirects=False).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(submit, ['Concurrent edit one', 'Concurrent edit two']))
        self.assertEqual(sorted(outcomes), [303, 400])
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Revision)), 2)

    def test_library_paginates_without_losing_records(self):
        for i in range(21): self.create(stem=f'Question number {i}')
        first = self.client.get('/teacher/questions').text
        second = self.client.get('/teacher/questions?page=2').text
        self.assertEqual(first.count('class="sr-only"> question'), 20)
        self.assertEqual(second.count('class="sr-only"> question'), 1)
        self.assertIn('Next page', first)
        self.assertNotIn('Next page', second)
