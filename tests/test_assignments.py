import re
import unittest
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import test_question_practice as practice_fixtures
from app.question_bank.models import Assignment,AssignmentItem,AssignmentRecipient,AssignmentAttempt,Question,Revision,Choice,AnswerKey,Attempt
from app.models import Group,Enrollment,User

class AssignmentTests(unittest.TestCase):
    setUp=practice_fixtures.QuestionPracticeTests.setUp
    token=practice_fixtures.QuestionPracticeTests.token
    login=practice_fixtures.QuestionPracticeTests.login
    values=practice_fixtures.QuestionPracticeTests.values
    post=practice_fixtures.QuestionPracticeTests.post
    create=practice_fixtures.QuestionPracticeTests.create
    ready=practice_fixtures.QuestionPracticeTests.ready
    answer_values=practice_fixtures.QuestionPracticeTests.answer_values

    def assigned(self):
        q=self.ready()
        self.client.post(f'/student/questions/{q}/answer',data=self.answer_values(q))
        self.login('teacher')
        page=self.client.get('/teacher/assignments/new')
        self.assertEqual(page.status_code,200,page.text)
        with Session(self.engine) as db:
            group=db.scalar(select(Group.id))
            revision=db.get(Question,q).published_revision_id
        data=dict(title='Week 1 practice',instructions='Try each question.',group_id=group,
            questions=[f'{q}:{revision}'],due='2026-01-01T12:00',csrf=self.token(page),
            submission_key=re.search(r'name="submission_key" value="([^"]+)"',page.text)[1])
        response=self.client.post('/teacher/assignments/new',data=data,follow_redirects=False)
        self.assertEqual(response.status_code,303,response.text)
        self.client.post('/teacher/assignments/new',data=data)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Assignment)),1)
            item=db.scalar(select(AssignmentItem)); aid=item.assignment_id;iid=item.id
        self.login('student')
        return q,aid,iid

    def form(self,aid,iid):
        url=f'/student/assignments/{aid}/questions/{iid}'
        page=self.client.get(url+'?retry=1')
        self.assertEqual(page.status_code,200,page.text)
        with Session(self.engine) as db:
            item=db.get(AssignmentItem,iid);key=db.get(AnswerKey,item.revision_id)
            wrong=db.scalar(select(Choice.id).where(Choice.revision_id==item.revision_id,Choice.id!=key.choice_id))
        return url,dict(csrf=self.token(page),retry_key=re.search(r'name="retry_key" value="([^"]+)"',page.text)[1],choice_id=wrong)

    def test_independent_progress_resume_retry_and_completion(self):
        q,aid,iid=self.assigned()
        overview=self.client.get(f'/student/assignments/{aid}')
        self.assertIn('0 of 1 answered',overview.text)
        self.assertIn('Start assignment',overview.text)
        url,data=self.form(aid,iid)
        result=self.client.post(url+'/answer',data=data)
        self.assertIn('Try again',result.text)
        self.assertNotIn('Correct answer:',result.text)
        self.assertNotIn('Two pairs make four.',result.text)
        self.client.post(url+'/answer',data=data)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(AssignmentAttempt)),1)
            self.assertEqual(db.scalar(select(func.count()).select_from(Attempt)),1)
        overview=self.client.get(f'/student/assignments/{aid}')
        self.assertIn('Completed',overview.text);self.assertIn('Late',overview.text)
        self.assertIn('Not yet correct',overview.text)
        url,data=self.form(aid,iid)
        result=self.client.post(url+'/answer',data=data)
        self.assertIn('Correct answer: B',result.text)
        self.assertIn('<details class="practice-explanation">',result.text)
        self.assertNotIn('practice-explanation" open',result.text)

    def test_recipients_csrf_and_cross_assignment_permissions(self):
        q,aid,iid=self.assigned();url,data=self.form(aid,iid)
        self.assertEqual(self.client.post(url+'/answer',data=dict(data,csrf='bad')).status_code,403)
        self.assertEqual(self.client.get('/teacher/assignments/new').status_code,403)
        self.assertEqual(self.client.get(f'/student/assignments/{aid+1}/questions/{iid}').status_code,404)
        with Session(self.engine) as db:
            db.scalar(select(Enrollment)).active=False;db.commit()
        self.assertEqual(self.client.post(url+'/answer',data=data).status_code,403)
        self.login('teacher')
        self.assertEqual(self.client.get(url).status_code,403)

    def test_snapshot_survives_unpublication_and_later_enrollment(self):
        q,aid,iid=self.assigned()
        with Session(self.engine) as db:
            db.get(Question,q).status='draft';db.commit()
        url,data=self.form(aid,iid)
        self.assertEqual(self.client.post(url+'/answer',data=data).status_code,200)
        with Session(self.engine) as db:
            from app.create_user import create_user
            from test_question_authoring import PASSWORD
            other=create_user(db,'later','Later fictional student',PASSWORD,'student')
            db.add(Enrollment(student_id=other.id,group_id=db.scalar(select(Group.id))));db.commit()
        self.login('later')
        self.assertEqual(self.client.get(url).status_code,404)
        self.assertNotIn('Week 1 practice',self.client.get('/student/assignments').text)

    def test_concurrent_retry_and_immutable_history(self):
        q,aid,iid=self.assigned();url,data=self.form(aid,iid)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.client.post(url+'/answer',data=data,follow_redirects=False),range(2)))
        self.assertEqual([r.status_code for r in results],[303,303])
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(AssignmentAttempt)),1)
            attempt=db.scalar(select(AssignmentAttempt));attempt.is_correct=True
            with self.assertRaises(IntegrityError):db.commit()

    def test_empty_group_and_stale_question_rejected(self):
        q=self.ready();self.login('teacher')
        page=self.client.get('/teacher/assignments/new')
        with Session(self.engine) as db:
            group=Group(name='Empty');db.add(group);db.commit();gid=group.id
            rid=db.get(Question,q).published_revision_id
        data=dict(title='Task',group_id=gid,questions=[f'{q}:{rid}'],csrf=self.token(page),
            submission_key=re.search(r'name="submission_key" value="([^"]+)"',page.text)[1])
        self.assertEqual(self.client.post('/teacher/assignments/new',data=data).status_code,400)
        with Session(self.engine) as db:
            data['group_id']=db.scalar(select(Enrollment.group_id));db.get(Question,q).status='draft';db.commit()
        self.assertEqual(self.client.post('/teacher/assignments/new',data=data).status_code,409)
        with Session(self.engine) as db:self.assertEqual(db.scalar(select(func.count()).select_from(Assignment)),0)

    def test_progress_resumes_at_next_unanswered_question(self):
        q,aid,iid=self.assigned()
        self.login('teacher')
        second=self.create(stem='Second task question')
        with Session(self.engine) as db:
            from app.question_bank.publication import publish_revision
            teacher=db.scalar(select(User.id).where(User.role=='teacher'))
            rid=db.get(Question,second).current_revision_id
            publish_revision(db,teacher,second,rid)
            db.add(AssignmentItem(assignment_id=aid,revision_id=rid,position=2));db.commit()
            second_item=db.scalar(select(AssignmentItem.id).where(AssignmentItem.position==2))
        self.login('student');url,data=self.form(aid,iid)
        self.client.post(url+'/answer',data=data)
        page=self.client.get(f'/student/assignments/{aid}')
        self.assertIn('In progress',page.text);self.assertIn('1 of 2 answered',page.text)
        self.assertIn(f'href="/student/assignments/{aid}/questions/{second_item}">Continue',page.text)
        self.assertIn('Week 1 practice',self.client.get('/student').text)

    def test_assignment_backup_restore_reconciles(self):
        from pathlib import Path
        from scripts.backup import backup, restore, inspect_database
        q,aid,iid=self.assigned();url,data=self.form(aid,iid)
        self.client.post(url+'/answer',data=data)
        source=Path(self.engine.url.database)
        copy=source.with_name('restored.db')
        bundle=backup(source,source.parent/'backups')['bundle']
        restore(bundle,copy)
        before,after=inspect_database(source),inspect_database(copy)
        self.assertEqual(before['fingerprints'],after['fingerprints'])
        self.assertEqual(after['counts']['qb_assignment_attempts'],1)
