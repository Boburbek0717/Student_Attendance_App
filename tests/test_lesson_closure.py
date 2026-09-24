from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from sqlalchemy import event, select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import test_lesson_management as fixtures
from app.lesson_management import close_permanently, closure_version, change_check_in
from app.attendance_corrections import correct_attendance, correction_context
from app.attendance import check_in
from app.database import initialize_database, make_engine
from app.models import Lesson, LessonClosure, Attendance
from app.packages import enrollment_balance


class ClosureTests(unittest.TestCase):
    setUp=fixtures.LessonManagementTests.setUp
    field=fixtures.LessonManagementTests.field
    login=fixtures.LessonManagementTests.login
    snapshot=fixtures.LessonManagementTests.snapshot

    def version(self):
        with Session(self.engine) as db:
            return closure_version(db,db.get(Lesson,self.lesson_id))

    def finish(self,action='finished',version=None):
        close_permanently(self.engine,self.teacher_id,self.lesson_id,action,'Class complete',version or self.version())

    def correct(self,action):
        with Session(self.engine) as db:
            version=correction_context(db,self.lesson_id,self.enrollment_id)['version']
        correct_attendance(self.engine,self.teacher_id,self.lesson_id,self.enrollment_id,action,'Teacher review',version)

    def test_finish_blocks_code_reopen_but_allows_corrections(self):
        code,version,_=self.snapshot()
        self.finish()
        with self.assertRaises(ValueError):check_in(self.engine,self.student_id,code)
        with self.assertRaises(ValueError):change_check_in(self.engine,self.teacher_id,self.lesson_id,version,reopen=True)
        self.correct('present');self.correct('reverse')
        with Session(self.engine) as db:
            self.assertEqual(enrollment_balance(db,self.enrollment_id)['balance'],12)
        page=self.client.get(self.url)
        self.assertIn('Finished permanently',page.text)
        self.assertNotIn('Reopen check-in for this lesson',page.text)
        self.assertIn('Absence finalized',page.text)
        with self.assertRaises(ValueError):self.finish()

    def test_cancellation_preserved_and_not_absent(self):
        self.finish('cancelled')
        page=self.client.get(self.url)
        self.assertIn('Cancelled permanently',page.text)
        self.assertNotIn('Absent ·',page.text)
        self.assertIn('Cancelled — no absences',self.client.get(self.history).text)
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):self.correct('present')
        with Session(self.engine) as db:self.assertIsNotNone(db.get(Lesson,self.lesson_id))

    def test_reversed_attendance_prevents_cancellation(self):
        self.correct('present');self.correct('reverse')
        with self.assertRaisesRegex(ValueError,'no attendance history'):self.finish('cancelled')

    def test_stale_attendance_and_correction_previews(self):
        version=self.version();self.correct('present')
        with self.assertRaisesRegex(ValueError,'changed'):self.finish(version=version)
        version=self.version();self.correct('reverse')
        with self.assertRaisesRegex(ValueError,'changed'):self.finish(version=version)

    def test_http_permission_csrf_and_preview(self):
        url=self.url+'/finish'
        page=self.client.get(url)
        self.assertEqual(page.status_code,200)
        self.assertIn('cannot be reopened',page.text)
        self.assertEqual(self.client.post(url).status_code,403)
        data={'csrf':self.field(page,'csrf'),'expected_version':self.field(page,'expected_version'),'action':'finished','reason':'Class complete'}
        self.login('student')
        self.assertEqual(self.client.get(url).status_code,403)
        self.assertEqual(self.client.post(url,data=data).status_code,403)
        self.login('teacher');page=self.client.get(url);data['csrf']=self.field(page,'csrf')
        self.assertEqual(self.client.post(url,data=data,follow_redirects=False).status_code,303)

    def test_cancel_and_checkin_serialize(self):
        code=self.snapshot()[0];version=self.version();barrier=Barrier(2)
        def cancel():
            barrier.wait()
            try:self.finish('cancelled',version)
            except ValueError:pass
        def attend():
            barrier.wait()
            try:check_in(self.engine,self.student_id,code)
            except ValueError:pass
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(cancel);b=pool.submit(attend);a.result();b.result()
        with Session(self.engine) as db:
            count=db.scalar(select(func.count()).select_from(Attendance))
            cancelled=db.get(LessonClosure,self.lesson_id) is not None
            self.assertEqual(count,0 if cancelled else 1)

    def test_audit_failure_rolls_back_code_close(self):
        before=self.snapshot()
        def fail(conn,cursor,statement,parameters,context,executemany):
            if statement.startswith('INSERT INTO lesson_closures'):
                raise IntegrityError(statement,parameters,Exception('test'))
        event.listen(self.engine,'before_cursor_execute',fail)
        try:
            with self.assertRaises(ValueError):self.finish()
        finally:event.remove(self.engine,'before_cursor_execute',fail)
        self.assertEqual(self.snapshot(),before)

    def test_additive_upgrade_and_restored_closure(self):
        LessonClosure.__table__.drop(self.engine)
        initialize_database(self.engine);initialize_database(self.engine)
        self.finish()
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/'restore.db')
            with closing(sqlite3.connect(self.engine.url.database)) as source, closing(sqlite3.connect(path)) as backup:
                source.backup(backup)
                self.assertEqual(backup.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                self.assertEqual(backup.execute('PRAGMA foreign_key_check').fetchall(),[])
            restored=make_engine(path)
            try:
                with Session(restored) as db:
                    self.assertEqual(db.get(LessonClosure,self.lesson_id).status,'finished')
                    self.assertEqual(enrollment_balance(db,self.enrollment_id)['balance'],12)
                with self.assertRaises(ValueError):change_check_in(restored,self.teacher_id,self.lesson_id,'',reopen=True)
            finally:restored.dispose()

    def test_legacy_finish_freezes_roster(self):
        from app.models import LessonRoster, LessonRosterSnapshot, Enrollment
        from sqlalchemy import delete
        with Session(self.engine) as db:
            db.execute(delete(LessonRoster).where(LessonRoster.lesson_id==self.lesson_id))
            db.execute(delete(LessonRosterSnapshot).where(LessonRosterSnapshot.lesson_id==self.lesson_id))
            db.commit()
        self.assertIn('freeze the current active roster',self.client.get(self.url+'/finish').text)
        self.finish()
        with Session(self.engine) as db:
            db.get(Enrollment,self.enrollment_id).active=False
            db.commit()
        self.assertIn('Absent · 1',self.client.get(self.url).text)
