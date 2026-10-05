"""Local, disposable portfolio sandbox. Never accepts an existing database path."""
from contextlib import contextmanager
from datetime import timedelta
import hashlib
from pathlib import Path
import re
import secrets
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.isolated import isolated_imports

# Intentionally public credentials for fictional data only, not an application secret.
DEMO_PASSWORD = 'Explore-SAT-Factory!'


def seed(engine):
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from app.models import (User, Group, Enrollment, LessonPackage, Lesson, Attendance,
                            LessonRosterSnapshot, LessonRoster, LessonClosure, utc_now)
    from app.security import password_hasher
    from app.question_bank.models import (Skill, Question, Revision, Choice, AnswerKey,
                                          Assignment, AssignmentItem, AssignmentRecipient)
    from app.question_bank.publication import publish_revision
    with Session(engine) as db:
        if db.scalar(select(User.id).limit(1)) is not None:
            raise ValueError('Demo seeding requires an empty database.')
        hashed = password_hasher.hash(DEMO_PASSWORD)
        teacher = User(username='demo-teacher', display_name='Demo Teacher', role='teacher', password_hash=hashed)
        group = Group(name='Demo SAT practice')
        db.add_all([teacher, group]); db.flush()
        students = []
        for number in range(6):
            student = User(username='demo-student' if number == 0 else f'demo-student-{number}',
                           display_name=f'Fictional Student {number + 1}', role='student', password_hash=hashed)
            db.add(student); db.flush(); students.append(student)
            enrollment = Enrollment(student_id=student.id, group_id=group.id)
            db.add(enrollment); db.flush()
            package = LessonPackage(enrollment_id=enrollment.id, purchased_at=utc_now()-timedelta(days=7))
            db.add(package); db.flush()
        lesson = Lesson(group_id=group.id, started_at=utc_now()-timedelta(days=1))
        db.add(lesson); db.flush()
        db.add(LessonRosterSnapshot(lesson_id=lesson.id, captured_at=lesson.started_at)); db.flush()
        memberships = db.scalars(select(Enrollment)).all()
        for index, enrollment in enumerate(memberships):
            db.add(LessonRoster(lesson_id=lesson.id, enrollment_id=enrollment.id))
            if index < 4:
                package_id = db.scalar(select(LessonPackage.id).where(LessonPackage.enrollment_id == enrollment.id))
                db.add(Attendance(lesson_id=lesson.id, enrollment_id=enrollment.id, package_id=package_id, checked_in_at=lesson.started_at+timedelta(minutes=2)))
        db.add(LessonClosure(lesson_id=lesson.id, teacher_id=teacher.id, status='finished', reason='Fictional completed class', created_at=lesson.started_at+timedelta(hours=1)))
        samples = [
            ('Linear equations in one variable', 'If 3x + 5 = 20, what is x?', ['3', '5', '15', '25'], 1, 'Subtract 5, then divide by 3.'),
            ('Transitions', 'Which transition best completes the text?', ['However,', 'For example,', 'Similarly,', 'Meanwhile,'], 0,
             'However introduces the contrast between the forecast and the actual weather.'),
            ('Boundaries', 'Which choice correctly joins two complete sentences?', ['The class ended, we left.', 'The class ended we left.', 'The class ended; we left.', 'The class ended: and we left.'], 2,
             'A semicolon can join two closely related independent clauses.'),
        ]
        revisions = []
        for category, stem, options, correct, explanation in samples:
            question = Question(created_by=teacher.id)
            db.add(question); db.flush()
            revision = Revision(question_id=question.id, number=1,
                skill_id=db.scalar(select(Skill.id).where(Skill.name == category)), difficulty='easy',
                stem=stem, passage='The forecast predicted rain. ____ the sky stayed clear all day.' if category == 'Transitions' else '',
                explanation=explanation, content_hash=hashlib.sha256(stem.encode()).hexdigest(), created_by=teacher.id)
            db.add(revision); db.flush()
            choices = [Choice(revision_id=revision.id, position=i, text=value) for i, value in enumerate(options)]
            db.add_all(choices); db.flush()
            db.add(AnswerKey(revision_id=revision.id, choice_id=choices[correct].id)); db.flush()
            question.current_revision_id = revision.id; db.flush()
            publish_revision(db, teacher.id, question.id, revision.id)
            revisions.append(revision)
        assignment = Assignment(title='Demo: three quick questions', instructions='Explore answering and reviewing an assignment.',
            group_id=group.id, created_by=teacher.id, due_at=utc_now()+timedelta(days=7), submission_key=secrets.token_hex(32))
        db.add(assignment); db.flush()
        for position, revision in enumerate(revisions, 1):
            db.add(AssignmentItem(assignment_id=assignment.id, revision_id=revision.id, position=position))
        for student in students:
            db.add(AssignmentRecipient(assignment_id=assignment.id, student_id=student.id))
        db.commit()


class ProtectDemoAccess:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        from starlette.responses import HTMLResponse
        from app.middleware import SECURITY_HEADERS
        path = scope.get('path', '').rstrip('/')
        if scope['type'] == 'http' and scope['method'] not in ('GET', 'HEAD', 'OPTIONS') and re.fullmatch(
                r'/teacher/students/[^/]+/(?:profile|password|enrollments/[^/]+/status)', path):
            response = HTMLResponse('<h1>Demo access is protected</h1><p>Account details, passwords and enrollment access cannot be changed in this shared demo.</p><a href="/teacher/students">Return to students</a>',
                                    status_code=403, headers={'Cache-Control': 'no-store', **SECURITY_HEADERS})
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


@contextmanager
def portfolio_demo(*, public=False, allowed_hosts=None):
    # Keep the import guard active for the entire application lifetime.
    with isolated_imports(), tempfile.TemporaryDirectory(prefix='sat-portfolio-') as directory:
        from app.database import make_engine, initialize_database
        from app.main import create_app
        from starlette.middleware.sessions import SessionMiddleware
        engine = make_engine(str(Path(directory) / 'fictional.sqlite3'))
        try:
            initialize_database(engine)
            seed(engine)
            app = create_app(engine, secrets.token_hex(32), production=public, allowed_hosts=allowed_hosts)
            app.state.portfolio_demo = True
            from starlette.middleware import Middleware
            app.user_middleware.append(Middleware(ProtectDemoAccess))
            if public:
                from scripts.demo_host import DemoLimits
                # Inside host/security middleware, before request bodies are buffered.
                from app.middleware import RequestBodyLimit
                position = next(i for i, item in enumerate(app.user_middleware) if item.cls is RequestBodyLimit)
                app.user_middleware.insert(position, Middleware(DemoLimits))
                app.state.public_demo = True
                from fastapi.responses import PlainTextResponse
                from sqlalchemy import text

                @app.get('/healthz', include_in_schema=False)
                def health():
                    try:
                        with engine.connect() as connection:
                            connection.execute(text('SELECT 1 FROM users LIMIT 1'))
                    except Exception:
                        return PlainTextResponse('Unavailable', status_code=503)
                    return PlainTextResponse('ok')

                @app.get('/robots.txt', include_in_schema=False)
                def robots():
                    return PlainTextResponse('User-agent: *\nDisallow: /\n')
            for middleware in app.user_middleware:
                if middleware.cls is SessionMiddleware:
                    middleware.kwargs['session_cookie'] = 'sat_portfolio_demo'
            yield app
        finally:
            engine.dispose()


def main():
    import uvicorn
    with portfolio_demo() as app:
        print('Local portfolio demo: http://127.0.0.1:8767/login; Ctrl+C removes fictional data.')
        uvicorn.run(app, host='127.0.0.1', port=8767, access_log=False, proxy_headers=False)


if __name__ == '__main__':
    main()
