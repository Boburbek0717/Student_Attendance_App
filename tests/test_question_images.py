import io
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import test_question_authoring as fixtures
from app.question_bank.models import Question, Revision, Media, MediaContent, Assignment, AssignmentItem, AssignmentRecipient
from app.question_bank.media import prepare_image, MAX_BYTES
from app.question_bank.publication import publish_revision
from app.models import User, Group, Enrollment


class QuestionImageTests(unittest.TestCase):
    setUp = fixtures.QuestionAuthoringTests.setUp
    token = fixtures.QuestionAuthoringTests.token
    login = fixtures.QuestionAuthoringTests.login
    values = fixtures.QuestionAuthoringTests.values
    post = fixtures.QuestionAuthoringTests.post

    def upload(self, path='/teacher/questions/new', **values):
        stream = io.BytesIO()
        Image.new('RGB', (120, 80), 'white').save(stream, format='PNG')
        return self.client.post(path, data=dict(self.values(**values), image_alt='Graph with x and y axes.',
            csrf=self.token(self.client.get('/teacher/questions/new'))),
            files={'image': ('graph.png', stream.getvalue(), 'image/png')}, follow_redirects=False)

    def saved(self):
        response = self.upload()
        self.assertEqual(response.status_code, 303, response.text)
        with Session(self.engine) as db:
            q = db.scalar(select(Question))
            return q.id, q.current_revision_id

    def test_upload_private_preview_publication_and_removal_preserve_history(self):
        q, revision = self.saved()
        url = f'/question-images/{revision}'
        self.assertIn(url, self.client.get(f'/teacher/questions/{q}/preview').text)
        image = self.client.get(url)
        self.assertEqual(image.status_code, 200)
        self.assertEqual(image.headers['content-type'], 'image/png')
        self.assertIn('no-store', image.headers['cache-control'])
        self.login('student')
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.cookies.clear()
        self.assertEqual(self.client.get(url).status_code, 404)
        with Session(self.engine) as db:
            teacher = db.scalar(select(User.id).where(User.role=='teacher'))
            publish_revision(db, teacher, q, revision); db.commit()
        page = self.client.get(f'/questions/{q}')
        self.assertIn(url, page.text)
        self.assertNotIn('Two pairs make four.', page.text)
        self.assertEqual(self.client.get(url).content, image.content)
        with Session(self.engine) as db:
            question=db.get(Question,q);question.status='draft';question.published_revision_id=None;db.commit()
        self.assertEqual(self.client.get(url).status_code, 404)
        self.login('teacher')
        response=self.post(f'/teacher/questions/{q}/edit',expected_revision=str(revision),stem='New text')
        self.assertEqual(response.status_code,303)
        with Session(self.engine) as db:
            current=db.get(Question,q).current_revision_id
            self.assertEqual(db.get(Revision,current).media_id,db.get(Revision,revision).media_id)
        response=self.post(f'/teacher/questions/{q}/edit',expected_revision=str(current),remove_image='1')
        self.assertEqual(response.status_code,303)
        with Session(self.engine) as db:
            self.assertIsNone(db.get(Revision,db.get(Question,q).current_revision_id).media_id)
            self.assertIsNotNone(db.get(Revision,revision).media_id)
        self.assertEqual(self.client.get(url).status_code,200)

    def test_invalid_payloads_and_missing_description_do_not_write(self):
        for payload in (b'<svg onload="alert(1)"></svg>', b'not an image', b'x'*(MAX_BYTES+1)):
            with self.assertRaises(ValueError): prepare_image(payload,'Description')
        stream=io.BytesIO();Image.new('RGB',(10,10)).save(stream,format='PNG')
        with self.assertRaises(ValueError):prepare_image(stream.getvalue(),'')
        csrf=self.token(self.client.get('/teacher/questions/new'))
        response=self.client.post('/teacher/questions/new',data=dict(self.values(),csrf=csrf),
            files={'image':('fake.png',b'not an image','image/png')})
        self.assertEqual(response.status_code,400)
        self.assertIn('What is 2 + 2?',response.text)
        with Session(self.engine) as db:self.assertEqual(db.scalar(select(func.count()).select_from(Media)),0)
        self.assertEqual(self.client.post('/teacher/questions/new',data=dict(self.values(),csrf='bad'),
            files={'image':('graph.png',stream.getvalue(),'image/png')}).status_code,403)

    def test_assignment_recipient_keeps_unpublished_image(self):
        q, revision=self.saved()
        with Session(self.engine) as db:
            teacher=db.scalar(select(User.id).where(User.role=='teacher'))
            student=db.scalar(select(User.id).where(User.role=='student'))
            group=Group(name='Fictional');db.add(group);db.flush()
            db.add(Enrollment(student_id=student,group_id=group.id))
            assignment=Assignment(title='Image practice',instructions='',group_id=group.id,created_by=teacher,submission_key='image-test')
            db.add(assignment);db.flush()
            db.add(AssignmentRecipient(assignment_id=assignment.id,student_id=student))
            item=AssignmentItem(assignment_id=assignment.id,revision_id=revision,position=1);db.add(item);db.flush()
            aid,iid=assignment.id,item.id;db.commit()
        self.login('student')
        url=f'/question-images/{revision}'
        self.assertIn(url,self.client.get(f'/student/assignments/{aid}/questions/{iid}').text)
        self.assertEqual(self.client.get(url).status_code,200)
        with Session(self.engine) as db:
            db.scalar(select(Enrollment)).active=False;db.commit()
        self.assertEqual(self.client.get(url).status_code,404)

    def test_sqlite_backup_restores_identical_image_and_immutable_records(self):
        from scripts.backup import backup,restore
        from app.database import make_engine
        q,revision=self.saved()
        with Session(self.engine) as db:
            media=db.scalar(select(Media));mid=media.id
            original=db.get(MediaContent,mid).data
            with self.assertRaises(IntegrityError):
                db.execute(text('UPDATE qb_media SET alt_text=:alt WHERE id=:id'),dict(alt='changed',id=mid))
            db.rollback()
        with tempfile.TemporaryDirectory() as directory:
            bundle=backup(self.engine.url.database,Path(directory)/'backups')['bundle']
            destination=Path(directory)/'restored.db';restore(bundle,destination)
            engine=make_engine(str(destination))
            try:
                with Session(engine) as db:self.assertEqual(db.get(MediaContent,mid).data,original)
            finally:engine.dispose()
