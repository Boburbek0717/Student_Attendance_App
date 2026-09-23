from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch
from sqlalchemy.orm import Session
from sqlalchemy import select
import test_lesson_management as fixtures
from app.school_time import school_time
from app.models import Lesson, LessonPackage, Attendance
from app.attendance import check_in


class SchoolTimeTests(unittest.TestCase):
    def test_midnight_and_aware_conversion(self):
        expected = "2026-01-01 04:30:00 Asia/Tashkent (UTC+05:00)"
        self.assertEqual(school_time(datetime(2025,12,31,23,30)), expected)
        self.assertEqual(school_time(datetime(2025,12,31,23,30,tzinfo=timezone.utc)), expected)
        self.assertEqual(school_time(datetime(2026,1,1,1,30,tzinfo=timezone(timedelta(hours=2)))), expected)


class SchoolTimePageTests(unittest.TestCase):
    setUp = fixtures.LessonManagementTests.setUp
    field = fixtures.LessonManagementTests.field
    login = fixtures.LessonManagementTests.login

    def test_same_local_date_across_roles_and_renewal(self):
        instant = datetime(2025,12,31,23,30)
        with Session(self.engine) as db:
            lesson=db.get(Lesson,self.lesson_id)
            lesson.started_at=instant
            lesson.code_expires_at=instant+timedelta(minutes=15)
            code=lesson.attendance_code
            db.scalar(select(LessonPackage)).purchased_at=instant
            db.commit()
        with patch('app.attendance.utc_now',return_value=instant+timedelta(seconds=1)):
            check_in(self.engine,self.student_id,code)
        with Session(self.engine) as db:
            db.scalar(select(Attendance)).checked_in_at=instant
            db.commit()
        expected=school_time(instant)
        for url in [self.url,self.history,f'/teacher/students/{self.student_id}/history',
                    f'/teacher/enrollments/{self.enrollment_id}/renew',
                    f'{self.url}/enrollments/{self.enrollment_id}/attendance']:
            page=self.client.get(url)
            self.assertEqual(page.status_code,200)
            self.assertIn(expected,page.text,url)
        self.login('student')
        self.assertIn(expected,self.client.get('/student').text)
        with Session(self.engine) as db:
            self.assertEqual(db.get(Lesson,self.lesson_id).started_at,instant)

    def test_expiry_still_uses_utc_at_exact_boundary(self):
        instant=datetime(2025,12,31,23,59)
        with Session(self.engine) as db:
            lesson=db.get(Lesson,self.lesson_id)
            lesson.started_at=instant-timedelta(minutes=15)
            lesson.code_expires_at=instant
            code=lesson.attendance_code
            db.commit()
        with patch('app.attendance.utc_now',return_value=instant):
            with self.assertRaisesRegex(ValueError,'expired'):
                check_in(self.engine,self.student_id,code)
