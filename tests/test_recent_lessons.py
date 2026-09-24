from datetime import timedelta
import unittest
from sqlalchemy.orm import Session
from sqlalchemy import func, select
import test_lesson_management as fixtures
from app.models import Lesson, Group, utc_now


class RecentLessonTests(unittest.TestCase):
    setUp = fixtures.LessonManagementTests.setUp
    field = fixtures.LessonManagementTests.field
    login = fixtures.LessonManagementTests.login
    snapshot = fixtures.LessonManagementTests.snapshot
    submit = fixtures.LessonManagementTests.submit

    def test_expired_lesson_stays_visible_and_reopens_same_id(self):
        with Session(self.engine) as db:
            db.get(Lesson,self.lesson_id).started_at=utc_now()-timedelta(minutes=20)
            db.get(Lesson,self.lesson_id).code_expires_at=utc_now()-timedelta(seconds=1)
            db.commit()
        page=self.client.get('/teacher')
        self.assertIn(f'Recent lesson #{self.lesson_id}',page.text)
        self.assertIn('Code expired',page.text)
        self.assertIn('Review / reopen this lesson',page.text)
        self.assertIn('Creates a separate class',page.text)
        self.assertEqual(self.submit('reopen').status_code,303)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Lesson)),1)
        page=self.client.get('/teacher')
        self.assertIn('Attendance code',page.text)
        self.assertNotIn('Code expired',page.text)

    def test_latest_started_lesson_not_future_or_other_group(self):
        self.submit('close')
        with Session(self.engine) as db:
            original=db.get(Lesson,self.lesson_id)
            db.add(Lesson(group_id=self.group_id,started_at=original.started_at-timedelta(days=1)))
            db.add(Lesson(group_id=self.group_id,started_at=utc_now()+timedelta(days=1)))
            other=Group(name='Empty group');db.add(other)
            db.commit()
        page=self.client.get('/teacher')
        self.assertEqual(page.text.count('Recent lesson #'),1)
        self.assertIn(f'Recent lesson #{self.lesson_id}',page.text)
        self.assertIn('Check-in closed',page.text)
        self.login('student')
        self.assertEqual(self.client.get('/teacher').status_code,403)

    def test_absence_hint_tracks_open_window(self):
        self.assertIn('Not checked in yet',self.client.get(self.url).text)
        self.submit('close')
        page=self.client.get(self.url)
        self.assertNotIn('Not checked in yet',page.text)
        self.assertIn('Check-in is closed',page.text)
