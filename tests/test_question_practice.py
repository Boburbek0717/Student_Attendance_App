import re
import unittest
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import test_question_authoring as fixtures
from app.models import Enrollment, Group, User
from app.question_bank.models import Question, Revision, Choice, AnswerKey, Attempt, PublicationEvent
from app.question_bank.publication import publish_revision
from app.create_user import create_user


class QuestionPracticeTests(unittest.TestCase):
    setUp=fixtures.QuestionAuthoringTests.setUp
    token=fixtures.QuestionAuthoringTests.token
    login=fixtures.QuestionAuthoringTests.login
    values=fixtures.QuestionAuthoringTests.values
    post=fixtures.QuestionAuthoringTests.post
    create=fixtures.QuestionAuthoringTests.create

    def ready(self):
        q=self.create()
        with Session(self.engine) as db:
            teacher=db.scalar(select(User).where(User.role=='teacher'))
            student=db.scalar(select(User).where(User.role=='student'))
            group=Group(name='Fictional practice');db.add(group);db.flush()
            db.add(Enrollment(student_id=student.id,group_id=group.id))
            revision=db.get(Question,q).current_revision_id
            publish_revision(db,teacher.id,q,revision);db.commit()
        self.login('student')
        return q

    def answer_values(self,q):
        page=self.client.get(f'/student/questions/{q}')
        def field(name): return re.search(fr'name="{name}" value="([^"]+)"',page.text).group(1)
        with Session(self.engine) as db:
            key=db.get(AnswerKey,int(field('revision_id')))
            choice_id=key.choice_id
        return dict(csrf=self.token(page),revision_id=field('revision_id'),retry_key=field('retry_key'),choice_id=choice_id)

    def test_answer_key_hidden_until_submission_and_retry_records_once(self):
        q=self.ready()
        page=self.client.get(f'/student/questions/{q}')
        self.assertNotIn('Two pairs make four.',page.text)
        self.assertNotIn('Correct answer:',page.text)
        data=self.answer_values(q)
        first=self.client.post(f'/student/questions/{q}/answer',data=data,follow_redirects=False)
        self.assertEqual(first.status_code,303)
        second=self.client.post(f'/student/questions/{q}/answer',data=data,follow_redirects=False)
        self.assertEqual(first.headers['location'],second.headers['location'])
        result=self.client.get(first.headers['location'])
        self.assertIn('Two pairs make four.',result.text)
        self.assertIn('Correct answer: B',result.text)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Attempt)),1)
        self.assertEqual(self.client.get(f'/student/questions/{q}?attempt=999').status_code,404)

    def test_roles_enrollment_and_csrf(self):
        q=self.create()
        self.assertEqual(self.client.get('/student/questions').status_code,403)
        self.login('student')
        self.assertEqual(self.client.get('/student/questions').status_code,403)
        self.login('teacher');q=self.ready()
        data=self.answer_values(q)
        self.assertEqual(self.client.post(f'/student/questions/{q}/answer',data=dict(data,csrf='wrong')).status_code,403)
        with Session(self.engine) as db:
            enrollment=db.scalar(select(Enrollment));enrollment.active=False;db.commit()
        self.assertEqual(self.client.post(f'/student/questions/{q}/answer',data=data).status_code,403)

    def test_unpublished_questions_and_cross_question_choices_denied(self):
        hidden=self.create(stem='Hidden draft secret')
        q=self.ready()
        self.assertNotIn('Hidden draft secret',self.client.get('/student/questions').text)
        self.assertEqual(self.client.get(f'/student/questions/{hidden}').status_code,404)
        data=self.answer_values(q)
        with Session(self.engine) as db:
            data['choice_id']=db.scalar(select(Choice.id).join(Revision,Choice.revision_id==Revision.id).where(Revision.question_id==hidden))
        self.assertEqual(self.client.post(f'/student/questions/{q}/answer',data=data).status_code,400)

    def test_concurrent_retries_record_one_attempt(self):
        q=self.ready();data=self.answer_values(q)
        def submit(_): return self.client.post(f'/student/questions/{q}/answer',data=data,follow_redirects=False)
        with ThreadPoolExecutor(max_workers=2) as pool: responses=list(pool.map(submit,range(2)))
        self.assertEqual([r.status_code for r in responses],[303,303])
        self.assertEqual(responses[0].headers['location'],responses[1].headers['location'])
        with Session(self.engine) as db: self.assertEqual(db.scalar(select(func.count()).select_from(Attempt)),1)

    def test_publication_withdrawal_audit_and_stale_actions(self):
        q=self.ready();data=self.answer_values(q)
        self.login('teacher')
        with Session(self.engine) as db:
            revision=db.get(Question,q).current_revision_id
            version=db.scalar(select(func.max(PublicationEvent.id)))
        response=self.post(f'/teacher/questions/{q}/publication',action='unpublish',revision_id=revision,version=version)
        self.assertEqual(response.status_code,303)
        self.post(f'/teacher/questions/{q}/publication',action='publish',revision_id=revision,version=version)
        with Session(self.engine) as db:
            self.assertEqual(db.get(Question,q).status,'draft')
            self.assertEqual(db.scalar(select(func.count()).select_from(PublicationEvent)),2)
            with self.assertRaises(IntegrityError): db.execute(text('DELETE FROM qb_publication_events'))
        self.login('student')
        self.assertEqual(self.client.get(f'/student/questions/{q}').status_code,404)

    def test_incomplete_publication_refused(self):
        q=self.create(explanation='')
        with Session(self.engine) as db:
            teacher=db.scalar(select(User.id).where(User.role=='teacher'))
            with self.assertRaises(ValueError): publish_revision(db,teacher,q,db.get(Question,q).current_revision_id)
            self.assertEqual(db.scalar(select(func.count()).select_from(PublicationEvent)),0)

    def test_other_student_cannot_read_attempt_or_its_explanation(self):
        q=self.ready()
        response=self.client.post(f'/student/questions/{q}/answer',data=self.answer_values(q),follow_redirects=False)
        with Session(self.engine) as db:
            other=create_user(db,'other','Other fictional student',fixtures.PASSWORD,'student')
            group=db.scalar(select(Group.id))
            db.add(Enrollment(student_id=other.id,group_id=group));db.commit()
        self.login('other')
        self.assertEqual(self.client.get(response.headers['location']).status_code,404)
        self.assertNotIn('Two pairs make four.',self.client.get(f'/student/questions/{q}').text)
