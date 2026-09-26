"""Fictional 30-student rehearsal; no live app imports before isolation."""
from contextlib import ExitStack
from datetime import timedelta
from pathlib import Path
import argparse
import json
import re
import secrets
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.isolated import isolated_imports


def fields(page):
    return dict(re.findall(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"', page.text))


def rehearse(directory):
    from fastapi.testclient import TestClient
    from sqlalchemy import select, func
    from sqlalchemy.orm import Session
    from app.database import make_engine
    from app.main import create_app
    from app.models import User, Group, Enrollment, Lesson, Attendance, AttendanceCorrection, LessonPackage, utc_now
    from app.security import password_hasher
    from app.packages import enrollment_balance, balance_version, set_balance

    engine = make_engine(str(Path(directory) / 'fictional.db'))
    app = create_app(engine, secrets.token_hex(32))
    outcomes = []
    def record(scenario, evidence):
        outcomes.append(dict(scenario=scenario, result='PASS', evidence=evidence))
    def balance(enrollment):
        with Session(engine) as db:
            return enrollment_balance(db, enrollment)
    def post(client, path, page, **extra):
        data = fields(page); data.update(extra)
        return client.post(path, data=data, follow_redirects=False)

    try:
        with ExitStack() as stack:
            teacher = stack.enter_context(TestClient(app))
            students = [stack.enter_context(TestClient(app)) for _ in range(30)]
            password = secrets.token_urlsafe(24)
            with Session(engine) as db:
                hashed = password_hasher.hash(password)
                owner = User(username='demo-teacher', display_name='Fictional Teacher', role='teacher', password_hash=hashed)
                db.add(owner)
                users = [User(username=f'demo-{i:02}', display_name=f'Fictional Student {i:02}', role='student', password_hash=hashed) for i in range(30)]
                db.add_all(users); db.commit()
                teacher_id = owner.id; user_ids = [u.id for u in users]
            start = time.perf_counter()
            for client, username in [(teacher, 'demo-teacher')] + [(c, f'demo-{i:02}') for i,c in enumerate(students)]:
                assert post(client, '/login', client.get('/login'), username=username, password=password).status_code == 303
            record('01 Login', f'1 teacher and 30 students from one simulated peer: {time.perf_counter()-start:.3f}s; no rejected logins')
            assert 'No group enrollments yet' in students[0].get('/student').text
            assert post(teacher, '/teacher/groups', teacher.get('/teacher'), group_name='Fictional Pilot').status_code == 303
            with Session(engine) as db:
                group_id = db.scalar(select(Group.id))
            for uid in user_ids:
                assert post(teacher, '/teacher/enrollments', teacher.get('/teacher'), student_id=uid, group_id=group_id).status_code == 303
            with Session(engine) as db:
                memberships = db.scalars(select(Enrollment.id).order_by(Enrollment.id)).all()
                assert db.scalar(select(func.count()).select_from(LessonPackage)) == 30
            assert all(balance(e)['balance'] == 12 for e in memberships)
            record('02 Enrollment', '30 separate 12-lesson packages; missing-enrollment guidance present before setup')
            assert post(teacher, f'/teacher/groups/{group_id}/lessons', teacher.get('/teacher')).status_code == 303
            with Session(engine) as db:
                lesson = db.scalar(select(Lesson)); lesson_id, code = lesson.id, lesson.attendance_code
            url = f'/teacher/lessons/{lesson_id}'
            assert 'Absent · 30' in teacher.get(url).text
            form = fields(students[0].get('/student')); form['code'] = code
            assert students[0].post('/student/check-in', data=form, follow_redirects=False).status_code == 303
            assert balance(memberships[0])['balance'] == 11
            assert 'Attendance recorded. One lesson has been used' in students[0].get('/student').text
            assert 'Present · 1' in teacher.get(url).text
            record('03 Check-in', 'One successful HTTP submission: 12 → 11; teacher shows present')
            assert students[0].post('/student/check-in', data=form, follow_redirects=False).status_code == 303
            assert 'Already checked in. No extra lesson was used.' in students[0].get('/student').text
            assert balance(memberships[0])['balance'] == 11
            record('04 Duplicate/lost response', 'Same form replayed without consuming first response: one attendance debit')
            with Session(engine) as db:
                lesson = db.get(Lesson, lesson_id)
                lesson.started_at = utc_now() - timedelta(minutes=20)
                lesson.code_expires_at = utc_now() - timedelta(minutes=1)
                db.commit()
            rejected = post(students[1], '/student/check-in', students[1].get('/student'), code=code)
            assert rejected.status_code == 400 and 'Ask your teacher for the current code' in rejected.text
            assert post(teacher, url+'/reopen', teacher.get(url)).status_code == 303
            with Session(engine) as db:
                assert db.scalar(select(func.count()).select_from(Lesson)) == 1
                code = db.get(Lesson, lesson_id).attendance_code
            assert post(students[1], '/student/check-in', students[1].get('/student'), code=code).status_code == 303
            record('05 Expiry/reopen', 'Expired code rejected with help; same lesson reopened and second student checked in')
            correction = url + f'/enrollments/{memberships[2]}/attendance'
            assert post(teacher, correction, teacher.get(correction), action='present', reason='Fictional phone failure').status_code == 303
            assert balance(memberships[2])['balance'] == 11
            assert post(teacher, correction, teacher.get(correction), action='reverse', reason='Fictional mistaken record').status_code == 303
            assert balance(memberships[2])['balance'] == 12
            with Session(engine) as db:
                assert db.scalars(select(AttendanceCorrection.action).order_by(AttendanceCorrection.id)).all() == ['manual', 'reverse']
                assert db.scalar(select(func.count()).select_from(Attendance)) == 3
            record('06 Correction', 'Teacher manual present/reversal: 12 → 11 → 12 with retained history')
            renewal = f'/teacher/enrollments/{memberships[0]}/renew'
            assert post(teacher, renewal, teacher.get(renewal)).status_code == 303
            assert balance(memberships[0])['balance'] == 23
            set_balance(engine, teacher_id, user_ids[3], memberships[3], 0, 'Fictional exhausted credit', balance_version(balance(memberships[3])))
            assert post(students[3], '/student/check-in', students[3].get('/student'), code=code).status_code == 303
            assert balance(memberships[3])['owed'] == 1
            renewal = f'/teacher/enrollments/{memberships[3]}/renew'
            assert post(teacher, renewal, teacher.get(renewal)).status_code == 303
            assert balance(memberships[3])['balance'] == 11
            record('07 Renewals', 'Early 11 + 12 = 23; exhausted credit permits attendance, 1 owed + renewal = 11 available')
            # Simultaneous independent clients, not a real Wi-Fi performance claim.
            from concurrent.futures import ThreadPoolExecutor
            payloads = [(client, fields(client.get('/student'))) for client in students[4:29]]
            start = time.perf_counter()
            def attend(pair):
                client, data = pair
                data['code'] = code
                return client.post('/student/check-in', data=data, follow_redirects=False).status_code
            with ThreadPoolExecutor(max_workers=25) as pool:
                assert list(pool.map(attend, payloads)) == [303] * 25
            record('07b Concurrent arrival', f'25 concurrent HTTP submissions passed in {time.perf_counter()-start:.3f}s; 30 logged-in students total')
            assert all(balance(e)['balance'] == 11 for e in memberships[4:29])
            assert post(teacher, url+'/finish', teacher.get(url+'/finish'), action='finished', reason='Fictional class complete').status_code == 303
            assert post(teacher, url+'/reopen', teacher.get(url)).status_code == 400
            assert post(students[29], '/student/check-in', students[29].get('/student'), code=code).status_code == 400
            assert balance(memberships[29])['balance'] == 12
            assert students[0].post('/student/check-in', data=form, follow_redirects=False).status_code == 303
            assert balance(memberships[0])['balance'] == 23
            assert post(teacher, correction, teacher.get(correction), action='present', reason='Fictional post-finish correction').status_code == 303
            assert balance(memberships[2])['balance'] == 11
            with Session(engine) as db:
                assert db.scalars(select(AttendanceCorrection.action).order_by(AttendanceCorrection.id)).all() == ['manual', 'reverse', 'restore']
            record('08 Permanent finish', 'Reopen rejected; original form receipt still works; audited correction after finish works')
            assert students[0].get(url).status_code == 403
            assert post(students[0], renewal, students[0].get('/student')).status_code == 403
            assert teacher.get('/student').status_code == 403
            assert teacher.post('/teacher/groups', data={'group_name':'Forged'}).status_code == 403
            assert 'Fictional phone failure' not in students[2].get('/student').text
            record('09 Boundaries', 'Student denied teacher read/write; teacher denied student page; missing CSRF rejected; private correction reason hidden')
            record('10 Message checks', 'Success, duplicate, expired and missing-enrollment messages checked in HTTP responses. Mobile/keyboard review recorded separately; no real-device claim.')
        return outcomes
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    with isolated_imports(), tempfile.TemporaryDirectory(prefix='sat-factory-rehearsal-') as directory:
        outcomes = rehearse(directory)
    report = json.dumps(outcomes, indent=2, ensure_ascii=False)
    if args.report:
        args.report.write_text(report + '\n', encoding='utf-8')
    print(json.dumps(outcomes, indent=2, ensure_ascii=True))


if __name__ == '__main__':
    main()
