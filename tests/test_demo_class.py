from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import unittest

from scripts.demo_class import main


class DemoClassTests(unittest.TestCase):
    def test_demo_uses_separate_cookie_and_removes_temporary_database(self):
        from fastapi.testclient import TestClient
        from sqlalchemy import select, func
        from sqlalchemy.orm import Session
        from app.models import User, Enrollment
        paths = []
        def review(app, **options):
            self.assertEqual(options['host'], '127.0.0.1')
            self.assertFalse(options['access_log'])
            self.assertFalse(options['proxy_headers'])
            paths.append(Path(app.state.database_engine.url.database))
            with TestClient(app) as client:
                cookie = client.get('/login').headers['set-cookie']
                self.assertTrue(cookie.startswith('sat_factory_demo_session='))
                with Session(app.state.database_engine) as db:
                    self.assertEqual(db.scalar(select(func.count()).select_from(User)), 31)
                    self.assertEqual(db.scalar(select(func.count()).select_from(Enrollment)), 30)
        output = StringIO()
        password = 'fictional test-only passphrase'
        with patch('scripts.demo_class.getpass.getpass', return_value=password), patch('uvicorn.run', side_effect=review), redirect_stdout(output):
            main()
        self.assertNotIn(password, output.getvalue())
        self.assertTrue(paths)
        self.assertFalse(paths[0].exists())

    def test_invalid_demo_password_stops_before_server_start(self):
        with patch('scripts.demo_class.getpass.getpass', return_value='short'), patch('uvicorn.run') as run:
            with self.assertRaises(SystemExit):
                main()
            run.assert_not_called()
