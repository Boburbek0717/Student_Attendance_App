import unittest
import test_auth as fixtures
from sqlalchemy.orm import Session
from app.models import Enrollment, Group


class OnboardingTests(unittest.TestCase):
    setUp = fixtures.AuthenticationTests.setUp
    token = fixtures.AuthenticationTests.token
    login = fixtures.AuthenticationTests.login

    def test_public_help_and_generic_failure_do_not_expose_account(self):
        page = self.client.get('/login')
        self.assertIn('First login or forgotten account details?', page.text)
        self.assertIn('contact your teacher directly', page.text)
        for username in ('madina', 'unknown-fictional-user'):
            response = self.login(username, 'wrong fictional password')
            self.assertEqual(response.status_code, 401)
            self.assertIn('Incorrect username or password.', response.text)
            self.assertIn('class="account-help" open', response.text)
            self.assertNotIn('wrong fictional password', response.text)
            self.assertNotIn('account does not exist', response.text.lower())

    def test_missing_enrollment_notice_and_checkin_recovery_help(self):
        self.login()
        page = self.client.get('/student')
        self.assertIn('you are not enrolled in a group yet', page.text)
        self.assertIn('retry the same form', page.text)
        self.assertIn('check Attendance history below', page.text)
        self.assertIn('ask your teacher to review attendance', page.text)
        with Session(self.engine) as db:
            group = Group(name='Fictional group'); db.add(group); db.flush()
            db.add(Enrollment(student_id=self.student_id, group_id=group.id, active=False))
            db.commit()
        page = self.client.get('/student')
        self.assertNotIn('you are not enrolled in a group yet', page.text)
        self.assertIn('Ask your teacher to check your membership', page.text)
        self.assertEqual(self.client.get('/teacher/students').status_code, 403)
