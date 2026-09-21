import base64
import contextlib
import io
import json
from pathlib import Path
import re
import tempfile
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.create_user import create_user, main as create_user_command
from app.database import initialize_database, make_engine
from app.main import create_app
from app.models import User
from app.security import password_hasher


PASSWORD = "test-only long passphrase"
COOKIE = "attendance_session"


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.engine = make_engine(str(Path(directory.name) / "test.db"))
        self.addCleanup(self.engine.dispose)
        self.app = create_app(self.engine, session_secret="test-only-secret")
        self.client = self.enterContext(TestClient(self.app))
        with Session(self.engine) as db:
            self.student_id = create_user(db, "madina", "Madina", PASSWORD, "student").id
            create_user(db, "teacher", "Teacher", PASSWORD, "teacher")

    def token(self, response):
        return re.search(r'name="csrf" value="([^"]+)"', response.text).group(1)

    def login(self, username="madina", password=PASSWORD):
        token = self.token(self.client.get("/login"))
        return self.client.post("/login", data={
            "username": username, "password": password, "csrf": token,
        }, follow_redirects=False)

    def test_password_is_salted_hash_and_username_normalized(self):
        with Session(self.engine) as db:
            user = create_user(db, "  ALI  ", " Ali ", PASSWORD, "student")
            self.assertEqual((user.username, user.display_name), ("ali", "Ali"))
            self.assertTrue(user.password_hash.startswith("$argon2id$"))
            self.assertNotEqual(user.password_hash, PASSWORD)
            self.assertTrue(password_hasher.verify(PASSWORD, user.password_hash))
            self.assertNotEqual(user.password_hash, db.get(User, self.student_id).password_hash)

    def test_invalid_accounts_and_duplicates_do_not_add_rows(self):
        with Session(self.engine) as db:
            for username, name, password, role in (
                ("invalid name", "Name", PASSWORD, "student"),
                ("valid", " ", PASSWORD, "student"),
                ("valid", "Name", "short", "student"),
                ("valid", "Name", "x" * 129, "student"),
                ("valid", "Name", PASSWORD, "admin"),
                (" MADINA ", "Duplicate", PASSWORD, "student"),
            ):
                with self.subTest(username=username, role=role, password_length=len(password)):
                    with self.assertRaises(ValueError):
                        create_user(db, username, name, password, role)
            self.assertEqual(db.scalar(select(func.count()).select_from(User)), 2)

    def test_anonymous_pages_require_login(self):
        for path in ("/teacher", "/student"):
            response = self.client.get(path, follow_redirects=False)
            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.headers["location"], "/login")

    def test_student_login_session_and_role_boundary(self):
        response = self.login(" MADINA ")
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/student")
        page = self.client.get("/student")
        self.assertIn("Welcome, Madina", page.text)
        self.assertEqual(page.headers["cache-control"], "no-store")
        self.assertEqual(self.client.get("/teacher").status_code, 403)
        self.assertEqual(self.client.get("/", follow_redirects=False).headers["location"], "/student")
        cookie_header = response.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie_header)
        self.assertIn("samesite=lax", cookie_header)
        self.assertIn("max-age=28800", cookie_header)
        data = json.loads(base64.b64decode(self.client.cookies[COOKIE].split(".")[0]))
        self.assertEqual(set(data), {"user_id", "csrf_token"})
        self.assertNotIn(PASSWORD, page.text)

    def test_teacher_login_and_role_boundary(self):
        response = self.login("teacher")
        self.assertEqual(response.headers["location"], "/teacher")
        self.assertIn("logged in as a teacher", self.client.get("/teacher").text)
        self.assertEqual(self.client.get("/student").status_code, 403)

    def test_login_errors_are_generic_and_do_not_echo_password(self):
        for username, password in (("madina", "wrong-password"), ("nobody", PASSWORD),
                                   ("' OR 1=1 --", PASSWORD), ("madina", "x" * 129)):
            response = self.login(username, password)
            self.assertEqual(response.status_code, 401)
            self.assertIn("Incorrect username or password.", response.text)
            self.assertNotIn(password, response.text)
            self.assertEqual(self.client.get("/student", follow_redirects=False).status_code, 303)

    def test_login_rejects_missing_wrong_and_other_browser_csrf(self):
        with TestClient(self.app) as other_browser:
            foreign_token = self.token(other_browser.get("/login"))
        self.client.get("/login")
        for token in ("", "wrong", "☃", foreign_token):
            response = self.client.post("/login", data={
                "username": "madina", "password": PASSWORD, "csrf": token,
            })
            self.assertEqual(response.status_code, 403)

    def test_logout_is_post_protected_and_clears_browser_session(self):
        old_token = self.token(self.client.get("/login"))
        self.login()
        token = self.token(self.client.get("/student"))
        self.assertNotEqual(old_token, token)
        self.assertEqual(self.client.get("/logout").status_code, 405)
        self.assertEqual(self.client.post("/logout", data={"csrf": old_token}).status_code, 403)
        self.assertEqual(self.client.get("/student").status_code, 200)
        response = self.client.post("/logout", data={"csrf": token}, follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertNotIn(COOKIE, self.client.cookies)
        self.assertEqual(self.client.get("/student", follow_redirects=False).status_code, 303)

    def test_tampered_cookie_cannot_impersonate_teacher(self):
        self.login()
        value = self.client.cookies[COOKIE]
        data, timestamp, signature = value.split(".")
        payload = json.loads(base64.b64decode(data))
        payload["user_id"] = self.student_id + 1
        tampered = base64.b64encode(json.dumps(payload).encode()).decode()
        self.client.cookies.clear()
        self.client.cookies.set(COOKIE, f"{tampered}.{timestamp}.{signature}")
        response = self.client.get("/teacher", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/login")

    def test_expired_cookie_requires_login(self):
        self.login()
        with patch("itsdangerous.TimestampSigner.get_timestamp", return_value=int(time.time()) + 28801):
            response = self.client.get("/student", follow_redirects=False)
        self.assertEqual(response.status_code, 303)

    def test_permissions_are_read_from_database_on_each_request(self):
        self.login()
        with Session(self.engine) as db:
            user = db.get(User, self.student_id)
            user.role = "teacher"
            db.commit()
        self.assertEqual(self.client.get("/student").status_code, 403)
        self.assertEqual(self.client.get("/teacher").status_code, 200)

    def test_deleted_user_loses_access(self):
        self.login()
        with Session(self.engine) as db:
            db.delete(db.get(User, self.student_id))
            db.commit()
        self.assertEqual(self.client.get("/student", follow_redirects=False).status_code, 303)

    def test_display_name_is_html_escaped(self):
        with Session(self.engine) as db:
            db.get(User, self.student_id).display_name = "<script>alert(1)</script>"
            db.commit()
        self.login()
        response = self.client.get("/student")
        self.assertNotIn("<script>", response.text)
        self.assertIn("&lt;script&gt;", response.text)

    def test_placeholder_hash_cannot_log_in(self):
        with Session(self.engine) as db:
            db.get(User, self.student_id).password_hash = "test-placeholder"
            db.commit()
        self.assertEqual(self.login().status_code, 401)

    def test_command_creates_account_without_printing_password(self):
        output = io.StringIO()
        with patch("sys.argv", ["create_user", "sardor", "--name", "Sardor"]), \
             patch("app.create_user.getpass.getpass", side_effect=[PASSWORD, PASSWORD]), \
             patch("app.create_user.engine", self.engine), \
             patch("app.create_user.initialize_database", side_effect=lambda: initialize_database(self.engine)), \
             contextlib.redirect_stdout(output):
            create_user_command()
        self.assertIn("Created student account: sardor", output.getvalue())
        self.assertNotIn(PASSWORD, output.getvalue())
        self.assertEqual(self.login("sardor").status_code, 303)

    def test_command_mismatch_does_not_create_account(self):
        with patch("sys.argv", ["create_user", "sardor", "--name", "Sardor"]), \
             patch("app.create_user.getpass.getpass", side_effect=[PASSWORD, "different"]), \
             patch("app.create_user.engine", self.engine), \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                create_user_command()
        self.assertEqual(error.exception.code, 1)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(User)), 2)


if __name__ == "__main__":
    unittest.main()
