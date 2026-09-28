import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import create_app
import test_question_authoring as fixtures


class ProductionSecurityTests(unittest.TestCase):
    setUp = fixtures.QuestionAuthoringTests.setUp
    token = fixtures.QuestionAuthoringTests.token
    login = fixtures.QuestionAuthoringTests.login

    def test_production_refuses_missing_secret_or_hosts(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ValueError): create_app(self.engine, production=True)
            with self.assertRaises(ValueError): create_app(self.engine, 'x'*64, production=True)
            for hosts in [['*'], ['https://example.test'], ['example.test:8000']]:
                with self.assertRaises(ValueError):
                    create_app(self.engine, 'x'*64, production=True, allowed_hosts=hosts)

    def test_https_cookies_hosts_headers_and_docs(self):
        app = create_app(self.engine, 'fictional-secret-'*5, production=True, allowed_hosts=['course.example.test'])
        with TestClient(app, base_url='https://course.example.test') as client:
            response=client.get('/login')
            self.assertEqual(response.status_code,200)
            cookie=response.headers['set-cookie'].lower()
            self.assertIn('secure',cookie); self.assertIn('httponly',cookie); self.assertIn('samesite=lax',cookie)
            self.assertEqual(response.headers['strict-transport-security'],'max-age=31536000')
            self.assertEqual(client.get('/login',headers={'host':'evil.example'}).status_code,400)
            for path in ['/docs','/redoc','/openapi.json']:
                self.assertEqual(client.get(path).status_code,404)
            response=client.get('http://course.example.test/login',follow_redirects=False)
            self.assertEqual(response.status_code,307)
            self.assertEqual(response.headers['location'],'https://course.example.test/login')
            self.assertNotIn('strict-transport-security',response.headers)
            response=client.get('http://course.example.test/login',headers={'x-forwarded-proto':'https'},follow_redirects=False)
            self.assertEqual(response.status_code,307)

    def test_local_http_still_works_and_validation_does_not_echo_input(self):
        response=self.client.get('/teacher/questions?theme_id=private-submitted-value')
        self.assertEqual(response.status_code,422)
        self.assertNotIn('private-submitted-value',response.text)
        self.assertNotIn('strict-transport-security',response.headers)
        self.assertEqual(response.headers['cache-control'],'no-store')
        self.assertEqual(self.client.get('/login',follow_redirects=False).status_code,303)
