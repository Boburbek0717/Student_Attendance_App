from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import unittest
from threading import Barrier
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import test_lesson_management as fixtures
from app.attendance import check_in
from app.attendance_corrections import correct_attendance, correction_context
from app.database import initialize_database, make_engine
from app.models import Attendance, AttendanceCorrection, Enrollment, Group, LessonPackage, LoginAttemptWindow, User
from app.packages import balance_version, enrollment_balance, renew_package, set_balance


class AttendanceCorrectionTests(unittest.TestCase):
    setUp = fixtures.LessonManagementTests.setUp
    field = fixtures.LessonManagementTests.field
    login = fixtures.LessonManagementTests.login
    snapshot = fixtures.LessonManagementTests.snapshot

    def context(self):
        with Session(self.engine) as db:
            return correction_context(db, self.lesson_id, self.enrollment_id)

    def correct(self, action, version=None, reason='Phone unavailable'):
        correct_attendance(self.engine, self.teacher_id, self.lesson_id, self.enrollment_id,
                           action, reason, version or self.context()['version'])

    def balance(self):
        with Session(self.engine) as db:
            return enrollment_balance(db, self.enrollment_id)

    def test_manual_reverse_restore_and_code_duplicate(self):
        original_version = self.context()['version']
        self.correct('present', original_version)
        self.assertEqual(self.balance()['balance'], 11)
        with self.assertRaises(ValueError):
            self.correct('present', original_version)
        with self.assertRaisesRegex(ValueError, 'already checked in'):
            check_in(self.engine, self.student_id, self.snapshot()[0])
        reverse_version = self.context()['version']
        self.correct('reverse', reverse_version)
        self.assertEqual(self.balance()['balance'], 12)
        with self.assertRaises(ValueError):
            self.correct('reverse', reverse_version)
        with self.assertRaisesRegex(ValueError, 'teacher reversed'):
            check_in(self.engine, self.student_id, self.snapshot()[0])
        self.correct('present')
        self.assertEqual(self.balance()['balance'], 11)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Attendance)), 1)
            self.assertEqual(db.scalars(select(AttendanceCorrection.action).order_by(AttendanceCorrection.id)).all(), ['manual','reverse','restore'])

    def test_reversal_after_renewal_and_correction(self):
        check_in(self.engine, self.student_id, self.snapshot()[0])
        b = self.balance()
        renew_package(self.engine, self.teacher_id, self.enrollment_id, b['latest_package_id'], b['attended'])
        b = self.balance()
        set_balance(self.engine, self.teacher_id, self.student_id, self.enrollment_id, 4, 'Credit correction', balance_version(b))
        self.correct('reverse')
        self.assertEqual(self.balance()['balance'], 5)
        self.correct('present')
        self.assertEqual(self.balance()['balance'], 4)
        self.assertEqual(sum(p['remaining'] for p in self.balance()['packages']), 4)

    def test_owed_lessons_and_renewal(self):
        b = self.balance()
        set_balance(self.engine, self.teacher_id, self.student_id, self.enrollment_id, 0, 'Credit correction', balance_version(b))
        self.correct('present')
        self.assertEqual(self.balance()['owed'], 1)
        b = self.balance()
        renew_package(self.engine, self.teacher_id, self.enrollment_id, b['latest_package_id'], b['attended'], b['latest_adjustment_id'], b['latest_correction_id'])
        self.assertEqual(self.balance()['balance'], 11)
        self.correct('reverse')
        self.assertEqual(self.balance()['balance'], 12)

    def test_reversal_restore_rejects_old_balance_forms_even_same_count(self):
        check_in(self.engine, self.student_id, self.snapshot()[0])
        old = self.balance()
        self.correct('reverse'); self.correct('present')
        with self.assertRaisesRegex(ValueError, 'balance changed'):
            renew_package(self.engine, self.teacher_id, self.enrollment_id, old['latest_package_id'], old['attended'])
        with self.assertRaisesRegex(ValueError, 'balance changed'):
            set_balance(self.engine, self.teacher_id, self.student_id, self.enrollment_id, 100, 'Stale correction', balance_version(old))

    def test_eligibility_and_inactive_saved_member(self):
        with Session(self.engine) as db:
            db.get(Enrollment, self.enrollment_id).active = False
            late = User(username='later', display_name='Later', role='student', password_hash='placeholder')
            db.add(late); db.flush()
            membership = Enrollment(student_id=late.id, group_id=self.group_id)
            db.add(membership); db.flush()
            late_id = membership.id
            db.commit()
        self.correct('present')
        self.correct('reverse')
        with Session(self.engine) as db:
            with self.assertRaises(HTTPException):
                correction_context(db, self.lesson_id, late_id)
            with self.assertRaises(HTTPException):
                correction_context(db, 2**80, self.enrollment_id)
        with self.assertRaises(HTTPException):
            correct_attendance(self.engine, self.student_id, self.lesson_id, self.enrollment_id, 'present','forged',self.context()['version'])

    def test_http_preview_permissions_history_and_privacy(self):
        url = self.url + f'/enrollments/{self.enrollment_id}/attendance'
        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertIn('After confirmation: <strong>11', page.text)
        self.assertEqual(self.balance()['balance'], 12)
        self.assertEqual(self.client.post(url).status_code, 403)
        data = {'csrf': self.field(page,'csrf'), 'expected_version': self.field(page,'expected_version'), 'action':'present','reason':'<script>Private reason</script>'}
        self.assertEqual(self.client.post(url, data=data, follow_redirects=False).status_code, 303)
        self.assertIn('&lt;script&gt;Private reason', self.client.get(url).text)
        self.assertIn('Present · 1', self.client.get(self.url).text)
        self.assertIn('1 checked in', self.client.get(self.history).text)
        self.login('student')
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url,data=data).status_code, 403)
        page = self.client.get('/student')
        self.assertIn('Teacher entry',page.text)
        self.assertIn('11 remaining',page.text)
        self.assertNotIn('Private reason',page.text)
        self.login('teacher')
        self.correct('reverse')
        self.assertIn('Absent · 1', self.client.get(self.url).text)
        self.assertIn('0 checked in', self.client.get(self.history).text)
        self.login('student')
        self.assertIn('Reversed — not charged', self.client.get('/student').text)

    def test_concurrent_manual_and_code_debit_once(self):
        version = self.context()['version']
        code = self.snapshot()[0]
        ready = Barrier(2)
        def manual():
            ready.wait(timeout=10)
            try:
                self.correct('present',version)
            except ValueError:
                pass
        def code_entry():
            ready.wait(timeout=10)
            try:
                check_in(self.engine,self.student_id,code)
            except ValueError:
                pass
        with ThreadPoolExecutor(max_workers=2) as pool:
            a,b=pool.submit(manual),pool.submit(code_entry)
            a.result(); b.result()
        self.assertEqual(self.balance()['balance'],11)
        self.assertTrue(self.context()['present'])

    def test_audit_insert_failure_rolls_back_attendance(self):
        def reject(conn,cursor,statement,parameters,context,executemany):
            if statement.startswith('INSERT INTO attendance_corrections'):
                raise IntegrityError(statement,parameters,Exception('simulated write failure'))
        event.listen(self.engine,'before_cursor_execute',reject)
        try:
            with self.assertRaises(ValueError):
                self.correct('present')
        finally:
            event.remove(self.engine,'before_cursor_execute',reject)
        self.assertEqual(self.balance()['balance'],12)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Attendance)),0)
        self.correct('present')
        self.assertEqual(self.balance()['balance'],11)

    def test_additive_schema_and_backup_restore(self):
        # Recreate the pre-sprint schema on this isolated database only.
        AttendanceCorrection.__table__.drop(self.engine)
        LoginAttemptWindow.__table__.drop(self.engine)
        initialize_database(self.engine)
        initialize_database(self.engine)
        self.assertEqual(self.balance()['balance'],12)
        self.correct('present'); self.correct('reverse')
        with tempfile.TemporaryDirectory() as folder:
            destination=str(Path(folder)/'restored.db')
            with closing(sqlite3.connect(self.engine.url.database)) as source, closing(sqlite3.connect(destination)) as restored:
                source.backup(restored)
                self.assertEqual(restored.execute('PRAGMA integrity_check').fetchall(),[('ok',)])
                self.assertEqual(restored.execute('PRAGMA foreign_key_check').fetchall(),[])
            restored_engine=make_engine(destination)
            try:
                initialize_database(restored_engine)
                with Session(restored_engine) as db:
                    self.assertEqual(enrollment_balance(db,self.enrollment_id)['balance'],12)
                    self.assertEqual(db.scalar(select(func.count()).select_from(AttendanceCorrection)),2)
            finally:
                restored_engine.dispose()
