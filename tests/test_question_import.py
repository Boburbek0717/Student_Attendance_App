import copy
import re
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func
from sqlalchemy.orm import Session
import test_question_authoring as fixtures
from app.question_bank.models import Question, Revision, PublicationEvent, Skill, Choice, AnswerKey
from app.question_bank.pdf_import import parse_pdf, ReviewStore


def sample():
    return dict(source_name='sample.pdf', source_sha256='a'*64, pages=1, rejected=[], candidates=[dict(
        source_id='abcdef12', page=1, assessment='PSAT 8/9', section='Reading and Writing',
        domain='Standard English Conventions', skill='Boundaries', difficulty='easy',
        passage='A fictional passage.', stem='Choose the answer.', choices=['First', 'Second', 'Third', 'Fourth'],
        answer=1, explanation='Fictional explanation.')])


class QuestionImportTests(unittest.TestCase):
    setUp = fixtures.QuestionAuthoringTests.setUp
    token = fixtures.QuestionAuthoringTests.token
    login = fixtures.QuestionAuthoringTests.login

    def upload(self, data=None):
        csrf = self.token(self.client.get('/teacher/questions/import'))
        with patch('app.question_bank.import_routes.parse_pdf', return_value=data or sample()):
            response = self.client.post('/teacher/questions/import', data={'csrf':csrf},
                files={'pdf':('sample.pdf', b'%PDF-fictional', 'application/pdf')}, follow_redirects=False)
        self.assertEqual(response.status_code, 303, response.text)
        return response.headers['location']

    def confirm(self, location, mode='draft', follow=True):
        csrf = self.token(self.client.get(location))
        return self.client.post(location, data={'csrf':csrf, 'mode':mode}, follow_redirects=follow)

    def test_upload_is_review_only_and_draft_import_is_idempotent(self):
        location = self.upload()
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Question)), 0)
        page = self.client.get(location)
        self.assertIn('Correct answer: B', page.text)
        first = self.confirm(location)
        self.assertIn('1 questions saved as drafts', first.text)
        self.confirm(location, 'publish')  # A retry cannot silently change the confirmed action.
        other = self.upload()
        self.assertIn('1 duplicates', self.client.get(other).text)
        self.confirm(other, 'publish')
        with Session(self.engine) as db:
            questions = db.scalars(select(Question)).all()
            self.assertEqual(len(questions), 1)
            self.assertEqual(questions[0].status, 'draft')
            revision = db.get(Revision, questions[0].current_revision_id)
            self.assertEqual(db.get(Skill, revision.skill_id).name, 'Boundaries')
            self.assertEqual(db.scalar(select(func.count()).select_from(PublicationEvent)), 0)

    def test_publish_is_atomic_and_records_teacher(self):
        location = self.upload()
        result = self.confirm(location, 'publish')
        self.assertIn('1 questions published', result.text)
        with Session(self.engine) as db:
            question = db.scalar(select(Question))
            self.assertEqual(question.status, 'published')
            event = db.scalar(select(PublicationEvent))
            self.assertEqual(event.teacher_id, question.created_by)
            self.assertEqual(db.scalar(select(func.count()).select_from(Choice)), 4)
            self.assertIsNotNone(db.get(AnswerKey, question.published_revision_id))

    def test_changed_duplicate_and_flagged_page_block_whole_import(self):
        self.confirm(self.upload())
        changed = sample(); changed['candidates'][0]['passage'] = 'Changed content'
        location = self.upload(changed)
        self.assertIn('different content', self.client.get(location).text)
        self.confirm(location)
        rejected = sample(); rejected['rejected'] = [dict(page=2, reason='Unsupported layout')]
        location = self.upload(rejected)
        self.assertNotIn('name="mode"', self.client.get(location).text)
        self.confirm(location)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Question)), 1)

    def test_permissions_csrf_and_review_bound_to_login(self):
        location = self.upload()
        self.assertEqual(self.client.post(location, data={'mode':'publish','csrf':'bad'}).status_code, 403)
        self.assertEqual(self.client.post('/teacher/questions/import', files={'pdf':('x.pdf',b'%PDF-')}, data={'csrf':'bad'}).status_code, 403)
        self.login('student')
        self.assertEqual(self.client.get('/teacher/questions/import').status_code, 403)
        self.assertEqual(self.client.get(location).status_code, 403)
        self.assertEqual(self.client.post(location, data={'mode':'publish'}).status_code, 403)
        self.login('teacher')
        self.assertEqual(self.client.get(location).status_code, 404)

    def test_expiry_and_bad_upload(self):
        location = self.upload()
        store = self.client.app.state.pdf_reviews
        store.entries[location.split('/')[-1]]['expires'] = 0
        self.assertEqual(self.client.get(location).status_code, 404)
        csrf = self.token(self.client.get('/teacher/questions/import'))
        response = self.client.post('/teacher/questions/import', data={'csrf':csrf}, files={'pdf':('x.pdf',b'not PDF')})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Choose a PDF', response.text)

    def test_mid_batch_failure_rolls_back_all_content_and_category(self):
        data = sample(); other = copy.deepcopy(data['candidates'][0]); other.update(source_id='abcdef34',page=2)
        data['candidates'].append(other);data['pages']=2
        location = self.upload(data)
        from app.question_bank.publication import publish_revision
        with patch('app.question_bank.pdf_import.publish_revision', side_effect=[None, ValueError('Simulated failure')]):
            self.confirm(location, 'publish')
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Question)), 0)
        self.assertIsNone(self.client.app.state.pdf_reviews.entries[location.split('/')[-1]]['result'])
        self.confirm(location,'publish')
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Question)), 2)

    def test_parallel_confirmation_adds_only_one_batch(self):
        location = self.upload()
        csrf = self.token(self.client.get(location))
        def submit(_):
            return self.client.post(location,data={'csrf':csrf,'mode':'publish'},follow_redirects=False)
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual([r.status_code for r in pool.map(submit,range(2))],[303,303])
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Question)), 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(PublicationEvent)), 1)

    def test_markup_escaped_and_upload_limit_is_narrow(self):
        data=sample();data['candidates'][0]['passage']='<script>alert(1)</script>'
        location=self.upload(data)
        self.assertIn('&lt;script&gt;', self.client.get(location).text)
        self.assertNotIn('<script>alert', self.client.get(location).text)
        self.assertEqual(self.client.post('/teacher/questions/new',content=b'x'*(192*1024+1)).status_code,413)
        self.assertEqual(self.client.post('/teacher/questions/import',content=b'x'*(10*1024*1024+65537)).status_code,413)

    def test_parser_timeout_and_invalid_pdf_are_visible(self):
        import subprocess
        with patch('app.question_bank.pdf_import.subprocess.run', side_effect=subprocess.TimeoutExpired('worker',25)):
            with self.assertRaisesRegex(ValueError,'too long'): parse_pdf(b'%PDF-fixture',ReviewStore())
        with self.assertRaisesRegex(ValueError,'could not be read'):
            parse_pdf(b'%PDF-malformed',ReviewStore())

    def test_flexible_new_math_category_publishes_and_reimport_skips(self):
        from scripts.flexible_pdf import parse_questions
        data=sample()
        data['candidates']=parse_questions('Assessment: Fictional SAT\nSection: Math\nDomain: Algebra\nCategory: New linear topic\nDifficulty: Easy\nQuestion 1\nSolve x + 2 = 5.\nA) 1\nB) 2\nC) 3\nD) 4\nAnswer: C',1)
        location=self.upload(data)
        response=self.confirm(location,'publish')
        self.assertEqual(response.status_code,200)
        with Session(self.engine) as db:
            q=db.scalar(select(Question));self.assertEqual(q.status,'published')
            skill=db.get(Skill,db.get(Revision,q.current_revision_id).skill_id)
            self.assertEqual(skill.name,'New linear topic')
        response=self.confirm(self.upload(data),'publish')
        self.assertIn('1 existing questions skipped',response.text)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Question)),1)
