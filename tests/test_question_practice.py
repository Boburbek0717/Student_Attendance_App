import re
import unittest
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import test_question_authoring as fixtures
from app.models import Enrollment, Group, User
from app.question_bank.models import Question, Revision, Choice, AnswerKey, Attempt, PublicationEvent, Skill
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
        self.assertIn('Attempt 1 saved.',self.client.get(f'/student/questions/{q}').text)
        self.assertNotIn('Two pairs make four.',self.client.get(f'/student/questions/{q}?retry=1').text)
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
        q=self.create(choice_3='')
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

    def test_themes_count_only_published_questions_and_scope_navigation(self):
        first = self.ready()
        self.login('teacher')
        second = self.create(passage='Second same-theme passage')
        with Session(self.engine) as db:
            other_skill = db.scalar(select(Skill.id).where(Skill.id != self.skill))
        other = self.create(skill_id=str(other_skill), passage='Different theme passage')
        hidden = self.create(passage='Unpublished passage')
        with Session(self.engine) as db:
            teacher = db.scalar(select(User.id).where(User.role == 'teacher'))
            for qid in (second, other):
                publish_revision(db, teacher, qid, db.get(Question, qid).current_revision_id)
            db.commit()
            theme_name = db.get(Skill, self.skill).name
        self.login('student')
        index = self.client.get('/student/questions')
        self.assertIn(theme_name, index.text)
        self.assertIn('2 questions', index.text)
        self.assertNotIn('Second same-theme passage', index.text)
        listing = self.client.get(f'/student/questions/themes/{self.skill}')
        self.assertEqual(listing.status_code, 200)
        self.assertIn('Second same-theme passage', listing.text)
        self.assertNotIn('Different theme passage', listing.text)
        self.assertNotIn('Unpublished passage', listing.text)
        page = self.client.get(f'/student/questions/{second}')
        self.assertIn(f'href="/student/questions/{first}"', page.text)
        self.assertNotIn(f'href="/student/questions/{other}"', page.text)
        self.assertIn(f'href="/student/questions/themes/{self.skill}"', page.text)
        self.assertEqual(self.client.get('/student/questions/themes/99999').status_code, 404)
        self.assertEqual(self.client.get(f'/student/questions/themes/{self.skill}?page=0').status_code, 400)
        with Session(self.engine) as db:
            db.scalar(select(Enrollment)).active = False
            db.commit()
        self.assertEqual(self.client.get(f'/student/questions/themes/{self.skill}').status_code, 403)

    def test_publish_and_answer_without_explanation_or_source(self):
        q = self.create(explanation='', source_name='', rights_note='', source_reference='')
        with Session(self.engine) as db:
            teacher = db.scalar(select(User.id).where(User.role == 'teacher'))
            student = db.scalar(select(User.id).where(User.role == 'student'))
            group = Group(name='Optional fields class'); db.add(group); db.flush()
            db.add(Enrollment(student_id=student, group_id=group.id))
            publish_revision(db, teacher, q, db.get(Question, q).current_revision_id)
            db.commit()
        self.login('student')
        response = self.client.post(f'/student/questions/{q}/answer', data=self.answer_values(q))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Correct answer: B', response.text)
        self.assertIn('Attempt 1 saved.', response.text)

    def test_repeat_publication_skips_content_reads_and_keeps_one_audit(self):
        from sqlalchemy import event
        q = self.ready()
        with Session(self.engine) as db:
            teacher = db.scalar(select(User.id).where(User.role == 'teacher'))
            revision = db.get(Question, q).current_revision_id
            statements = []
            def capture(conn, cursor, statement, params, context, many):
                if statement.lstrip().upper().startswith('SELECT'): statements.append(statement)
            event.listen(self.engine, 'before_cursor_execute', capture)
            try:
                publish_revision(db, teacher, q, revision)
            finally:
                event.remove(self.engine, 'before_cursor_execute', capture)
            self.assertLessEqual(len(statements), 2)
            self.assertEqual(db.scalar(select(func.count()).select_from(PublicationEvent)), 1)

    def test_correct_feedback_is_prominent_and_animates_only_once(self):
        q = self.ready()
        before = self.client.get(f'/student/questions/{q}')
        self.assertNotIn('id="answer-feedback"', before.text)
        self.assertNotIn('choice-correct', before.text)
        self.assertIn('/static/practice.css', before.text)
        response = self.client.post(f'/student/questions/{q}/answer', data=self.answer_values(q))
        self.assertIn('practice-feedback is-correct', response.text)
        self.assertIn('data-fresh="true"', response.text)
        self.assertIn('Correct answer · Your choice', response.text)
        again = self.client.get(f'/student/questions/{q}')
        self.assertIn('data-fresh="false"', again.text)
        self.assertIn('practice-feedback is-correct', again.text)

    def test_first_mistake_hides_answer_until_second_submission(self):
        q = self.ready()
        values = self.answer_values(q)
        with Session(self.engine) as db:
            wrong = db.scalar(select(Choice.id).where(Choice.revision_id == int(values['revision_id']), Choice.id != values['choice_id']))
        values['choice_id'] = wrong
        response = self.client.post(f'/student/questions/{q}/answer', data=values)
        self.assertIn('practice-feedback is-incorrect', response.text)
        self.assertIn('choice-incorrect', response.text)
        self.assertNotIn('choice-correct', response.text)
        self.assertIn('Your choice · Incorrect', response.text)
        self.assertNotIn('Correct answer:', response.text)
        self.assertNotIn('Two pairs make four.', response.text)
        self.assertIn('Try again', response.text)
        first_url = str(response.url)
        # Lost-response replays and refreshing do not consume another attempt.
        replay = self.client.post(f'/student/questions/{q}/answer', data=values)
        self.assertNotIn('Correct answer:', replay.text)
        self.assertNotIn('Correct answer:', self.client.get(first_url).text)
        retry = self.client.get(f'/student/questions/{q}?retry=1')
        values['retry_key'] = re.search(r'name="retry_key" value="([^"]+)"', retry.text)[1]
        second = self.client.post(f'/student/questions/{q}/answer', data=values)
        self.assertIn('Correct answer: B', second.text)
        self.assertIn('choice-correct', second.text)
        self.assertIn('Two pairs make four.', second.text)
        self.assertNotIn('Correct answer:', self.client.get(first_url).text)

    def test_new_category_and_question_inherit_practice_design(self):
        self.ready()
        self.login('teacher')
        with Session(self.engine) as db:
            domain = db.get(Skill, self.skill).domain_id
            skill = Skill(domain_id=domain, code='future-theme', name='Future category')
            db.add(skill); db.commit(); skill_id = skill.id
        q = self.create(skill_id=str(skill_id), stem='A newly added question')
        with Session(self.engine) as db:
            teacher = db.scalar(select(User.id).where(User.role=='teacher'))
            publish_revision(db, teacher, q, db.get(Question, q).current_revision_id)
            db.commit()
        self.login('student')
        index = self.client.get('/student/questions').text
        self.assertIn('Future category', index)
        self.assertIn('practice-theme-card', index)
        listing = self.client.get(f'/student/questions/themes/{skill_id}').text
        self.assertIn('practice-question-list', listing)
        page = self.client.get(f'/student/questions/{q}').text
        self.assertIn('/static/practice.css', page)
        self.assertIn('/static/practice-feedback.js', page)
        self.assertIn('practice-stage', page)

    def test_question_grid_results_are_personal_and_revision_scoped(self):
        from app.question_bank.practice import practice_statuses
        q = self.ready()
        with Session(self.engine) as db:
            revision = db.get(Revision, db.get(Question, q).published_revision_id)
            student = db.scalar(select(User.id).where(User.role=='student'))
            teacher = db.scalar(select(User.id).where(User.role=='teacher'))
            rows = [(db.get(Question,q), revision)]
            self.assertEqual(practice_statuses(db,student,rows), {})
        values = self.answer_values(q)
        correct = values['choice_id']
        with Session(self.engine) as db:
            values['choice_id'] = db.scalar(select(Choice.id).where(Choice.revision_id==int(values['revision_id']),Choice.id!=correct))
        self.client.post(f'/student/questions/{q}/answer',data=values)
        def status():
            with Session(self.engine) as db:
                revision = db.get(Revision,int(values['revision_id']))
                rows = [(db.get(Question,q),revision)]
                self.assertEqual(practice_statuses(db,teacher,rows), {})
                return practice_statuses(db,student,rows)[revision.id]
        self.assertEqual(status(),'incorrect')
        retry = self.client.get(f'/student/questions/{q}?retry=1')
        values['retry_key'] = re.search(r'name="retry_key" value="([^"]+)"',retry.text)[1]
        values['choice_id'] = correct
        self.client.post(f'/student/questions/{q}/answer',data=values)
        self.assertEqual(status(),'retried')
        page = self.client.get(f'/student/questions/themes/{self.skill}')
        self.assertIn('question-map-grid',page.text)
        self.assertIn('easy, Correct after a mistake',page.text)
        self.assertIn('aria-current="page"',self.client.get(f'/student/questions/{q}').text)

    def test_grid_first_try_correct(self):
        q = self.ready()
        self.client.post(f'/student/questions/{q}/answer',data=self.answer_values(q))
        page = self.client.get(f'/student/questions/themes/{self.skill}')
        self.assertIn('easy, First-try correct',page.text)
        self.assertIn('result-correct tile-result',page.text)
