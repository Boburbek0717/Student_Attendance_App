"""Repeatable classroom simulation using fictional accounts and a temporary database."""
from datetime import timedelta
from pathlib import Path
import json
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.database import make_engine
from app.main import create_app
from app.models import Attendance, Enrollment, Group, Lesson, LessonPackage, User, utc_now
from app.packages import balance_version, enrollment_balance, set_balance
from app.security import password_hasher


def csrf(response):
    return re.search(r'name="csrf" value="([^"]*)"', response.text).group(1)


def login(client, username):
    return client.post('/login', data={'username': username, 'password': 'fictional classroom password',
                                      'csrf': csrf(client.get('/login'))}, follow_redirects=False)


def main():
    results = {}
    with tempfile.TemporaryDirectory() as directory:
        engine = make_engine(str(Path(directory) / 'simulation.db'))
        app = create_app(engine, 'simulation-only-secret')
        with TestClient(app) as teacher, TestClient(app) as student:
            with Session(engine) as db:
                hashed = password_hasher.hash('fictional classroom password')
                owner = User(username='teacher', display_name='Demo Teacher', role='teacher', password_hash=hashed)
                group = Group(name='Demo SAT Evening')
                db.add_all([owner, group]); db.flush()
                teacher_id, group_id = owner.id, group.id
                student_ids, enrollment_ids = [], []
                for number in range(24):
                    user = User(username=f'demo{number:02}', display_name=f'Demo Student {number:02}', role='student', password_hash=hashed)
                    db.add(user); db.flush()
                    enrollment = Enrollment(student_id=user.id, group_id=group.id)
                    db.add(enrollment); db.flush()
                    db.add(LessonPackage(enrollment_id=enrollment.id))
                    student_ids.append(user.id); enrollment_ids.append(enrollment.id)
                db.commit()
            assert login(teacher, 'teacher').status_code == 303
            assert login(student, 'demo00').status_code == 303
            teacher.post(f'/teacher/groups/{group_id}/lessons', data={'csrf': csrf(teacher.get('/teacher'))})
            with Session(engine) as db:
                lesson = db.scalar(select(Lesson))
                lesson_id, code = lesson.id, lesson.attendance_code
            page = teacher.get(f'/teacher/lessons/{lesson_id}')
            results['class_start'] = {'check_in_open': 'Check-in open' in page.text, 'all_24_labelled_absent': 'Absent · 24' in page.text}
            token = csrf(student.get('/student'))
            first = student.post('/student/check-in', data={'csrf': token, 'code': code}, follow_redirects=False)
            repeat = student.post('/student/check-in', data={'csrf': token, 'code': code}, follow_redirects=False)
            with Session(engine) as db:
                results['normal_and_repeated_checkin'] = {'first_status': first.status_code, 'retry_status': repeat.status_code,
                    'attendance_rows': db.scalar(select(func.count()).select_from(Attendance)), 'balance': enrollment_balance(db, enrollment_ids[0])['balance']}
                b = enrollment_balance(db, enrollment_ids[1])
            set_balance(engine, teacher_id, student_ids[1], enrollment_ids[1], 11, 'Fictional offline student workaround', balance_version(b))
            page = teacher.get(f'/teacher/lessons/{lesson_id}')
            results['offline_student_balance_workaround'] = {'still_23_absent': 'Absent · 23' in page.text,
                'manual_attendance_route_exists': any('manual' in path for path in app.openapi()['paths'])}
            with Session(engine) as db:
                lesson = db.get(Lesson, lesson_id)
                lesson.started_at = utc_now() - timedelta(minutes=20)
                lesson.code_expires_at = utc_now() - timedelta(minutes=5)
                db.commit()
            expired = student.post('/student/check-in', data={'csrf': token, 'code': code})
            teacher.post(f'/teacher/groups/{group_id}/lessons', data={'csrf': csrf(teacher.get('/teacher'))})
            with Session(engine) as db:
                results['expired_code_and_new_lesson'] = {'expired_status': expired.status_code,
                    'lesson_count_after_start': db.scalar(select(func.count()).select_from(Lesson))}
            results['teacher_navigation'] = {'student_cards_on_main_page': teacher.get('/teacher').text.count('class="member"'),
                'setup_forms_before_roster': teacher.get('/teacher').text.index('Create a group') < teacher.get('/teacher').text.index('Groups and lesson packages')}
            results['local_time'] = {'timestamps_shown_in_utc': 'UTC' in page.text, 'school_timezone': 'Asia/Tashkent (UTC+05:00)'}
            home = student.get('/')
            results['visitor_journey'] = {'results_still_placeholder': 'No student result published' in home.text,
                'contact_or_enquiry_link': any(s in home.text for s in ('mailto:', 'tel:', 't.me/', '/contact', '/enquire'))}
            # Separate application instance gives the burst a clean login budget.
            # All clients use TestClient's same peer address, simulating classroom NAT.
            burst_app = create_app(engine, 'simulation-burst-secret')
            statuses = []
            with TestClient(burst_app) as burst:
                for number in range(12):
                    burst.cookies.clear()
                    statuses.append(login(burst, f'demo{number:02}').status_code)
            results['classroom_shared_ip_login_burst'] = {'statuses': statuses, 'successful': statuses.count(303), 'blocked': statuses.count(429)}
        engine.dispose()
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
