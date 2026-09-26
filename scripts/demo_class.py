"""Disposable fictional class for browser review; stop with Ctrl+C to remove data."""
from pathlib import Path
import getpass
import secrets
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.isolated import isolated_imports


def main():
    password = getpass.getpass('Choose a disposable demo password (12-128 characters): ')
    if not 12 <= len(password) <= 128:
        raise SystemExit('Use 12-128 characters. No demo was created.')
    with isolated_imports(), tempfile.TemporaryDirectory(prefix='sat-factory-browser-') as directory:
        from app.database import make_engine, initialize_database
        from app.models import User, Group, Enrollment, LessonPackage
        from app.security import password_hasher
        from app.main import create_app
        from sqlalchemy.orm import Session
        import uvicorn
        engine = make_engine(str(Path(directory) / 'fictional.sqlite3'))
        try:
            initialize_database(engine)
            with Session(engine) as db:
                hashed = password_hasher.hash(password)
                db.add(User(username='demo-teacher', display_name='Fictional Teacher', role='teacher', password_hash=hashed))
                group = Group(name='Fictional SAT classroom with a deliberately long group name')
                db.add(group); db.flush()
                for number in range(30):
                    student = User(username=f'demo-{number:02}', display_name=f'Fictional Student {number:02} With A Long Display Name', role='student', password_hash=hashed)
                    db.add(student); db.flush()
                    membership = Enrollment(student_id=student.id, group_id=group.id)
                    db.add(membership); db.flush()
                    db.add(LessonPackage(enrollment_id=membership.id))
                db.commit()
            password = None
            app = create_app(engine, secrets.token_hex(32))
            # Cookies share a hostname across ports. Never replace the real app's cookie.
            from starlette.middleware.sessions import SessionMiddleware
            for middleware in app.user_middleware:
                if middleware.cls is SessionMiddleware:
                    middleware.kwargs['session_cookie'] = 'sat_factory_demo_session'
            print('Fictional demo: http://127.0.0.1:8766/login; demo-teacher and demo-00 through demo-29. Ctrl+C removes the demo.')
            uvicorn.run(app, host='127.0.0.1', port=8766, access_log=False, proxy_headers=False)
        finally:
            engine.dispose()


if __name__ == '__main__':
    main()
