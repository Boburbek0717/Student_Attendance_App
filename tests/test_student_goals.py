import unittest
from datetime import date
from pathlib import Path
from sqlalchemy.orm import Session
from app.models import StudentGoal
from app.database import initialize_database
import test_auth as fixtures
from scripts.backup import backup, restore, inspect_database

class StudentGoalTests(unittest.TestCase):
    setUp = fixtures.AuthenticationTests.setUp
    token = fixtures.AuthenticationTests.token
    login = fixtures.AuthenticationTests.login

    def save(self, **values):
        data = dict(target_score='1400', version='0',
                    csrf=self.token(self.client.get('/student')))
        data.update(values)
        return self.client.post('/student/goal', data=data, follow_redirects=False)

    def test_save_edit_clear_and_stale_tab(self):
        self.login()
        self.assertEqual(self.save().status_code, 303)
        page=self.client.get('/student')
        self.assertIn('1400', page.text)
        self.assertNotIn('Exam date', page.text)
        self.assertEqual(self.save(target_score='1500').status_code,409)
        self.assertEqual(self.save(target_score='1500', version='1').status_code,303)
        self.assertEqual(self.save(target_score='', exam_date='', version='2').status_code,303)
        with Session(self.engine) as db:
            goal=db.get(StudentGoal,self.student_id)
            self.assertEqual((goal.target_score,goal.exam_date,goal.version),(None,None,3))

    def test_validation_and_authorization(self):
        self.assertEqual(self.client.post('/student/goal',data={},follow_redirects=False).status_code,303)
        self.login()
        for values in ({'target_score':'399'}, {'target_score':'1601'}, {'target_score':'1405'},
                       {'target_score':'1e3'}, {'version':'-1'}):
            self.assertEqual(self.save(**values).status_code,400)
        self.assertEqual(self.save(csrf='bad').status_code,403)
        self.assertEqual(self.save(student_id='999').status_code,303)
        with Session(self.engine) as db:
            self.assertIsNone(db.get(StudentGoal,999))
            self.assertIsNotNone(db.get(StudentGoal,self.student_id))
        self.login('teacher')
        self.assertEqual(self.client.post('/student/goal',data={'csrf':'unused'}).status_code,403)

    def test_retired_exam_date_is_not_displayed_or_changed(self):
        self.login(); self.save()
        with Session(self.engine) as db:
            db.get(StudentGoal,self.student_id).exam_date=date(2026,12,5)
            db.commit()
        self.assertEqual(self.save(target_score='1500',version='1',exam_date='2030-01-01').status_code,303)
        page=self.client.get('/student')
        self.assertNotIn('Exam date',page.text)
        self.assertNotIn('days to go',page.text)
        self.assertNotIn('05 Dec 2026',page.text)
        with Session(self.engine) as db:
            self.assertEqual(db.get(StudentGoal,self.student_id).exam_date,date(2026,12,5))

    def test_goal_upgrade_and_backup_restore(self):
        self.login(); self.save()
        root=Path(self.engine.url.database).parent
        bundle=backup(self.engine.url.database,root/'backups')['bundle']
        restored=root/'restored.db'
        restore(bundle,restored)
        self.assertEqual(inspect_database(restored)['fingerprints']['student_goals'],
                         inspect_database(self.engine.url.database)['fingerprints']['student_goals'])
        # An older database has no goal table. Backup still works before upgrading.
        with self.engine.begin() as connection:
            StudentGoal.__table__.drop(connection)
        inspect_database(self.engine.url.database)
        initialize_database(self.engine)
        initialize_database(self.engine)
        with Session(self.engine) as db:
            self.assertIsNone(db.get(StudentGoal,self.student_id))

    def test_other_student_cannot_see_goal_and_concurrent_save_is_guarded(self):
        from app.create_user import create_user
        from concurrent.futures import ThreadPoolExecutor
        self.login()
        data=dict(target_score='1500',exam_date='2026-12-05',version='0',csrf=self.token(self.client.get('/student')))
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(lambda _:self.client.post('/student/goal',data=data,follow_redirects=False),range(2)))
        self.assertEqual(sorted(r.status_code for r in responses),[303,409])
        with Session(self.engine) as db:
            create_user(db,'other','Fictional other',fixtures.PASSWORD,'student')
        self.login('other')
        page=self.client.get('/student')
        self.assertNotIn('05 Dec 2026',page.text)
        self.assertIn('Set target',page.text)
        self.assertNotIn('1500',page.text)
