from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.attendance_state import attendance_active
from app.database import write_transaction
from app.models import LessonClosure, Attendance, AttendanceCorrection, Enrollment, Group, Lesson, LessonRoster, LessonRosterSnapshot, User, utc_now
from app.packages import balance_version, enrollment_balance
from app.security import current_user, verify_csrf
from app.teacher import require_teacher
from app.web import get_db, render

router = APIRouter(prefix='/teacher/lessons')


def correction_context(db, lesson_id, enrollment_id):
    if not (0 < lesson_id < 2**63 and 0 < enrollment_id < 2**63):
        raise HTTPException(404, 'Lesson enrollment not found.')
    lesson, enrollment = db.get(Lesson, lesson_id), db.get(Enrollment, enrollment_id)
    if lesson is None or enrollment is None or lesson.group_id != enrollment.group_id:
        raise HTTPException(404, 'Lesson enrollment not found.')
    closure = db.get(LessonClosure, lesson_id)
    if closure and closure.status == 'cancelled':
        raise HTTPException(403, 'Cancelled lessons cannot receive attendance.')
    student = db.get(User, enrollment.student_id)
    if student is None or student.role != 'student':
        raise HTTPException(404, 'Student not found.')
    record = db.scalar(select(Attendance).where(Attendance.lesson_id == lesson_id, Attendance.enrollment_id == enrollment_id))
    snapshot = db.get(LessonRosterSnapshot, lesson_id)
    roster_member = db.get(LessonRoster, (lesson_id, enrollment_id))
    eligible = record is not None or roster_member is not None or (snapshot is None and enrollment.active)
    if not eligible or lesson.started_at > utc_now():
        raise HTTPException(403, 'This student is not eligible for a correction on this lesson.')
    history = db.execute(select(AttendanceCorrection, User.display_name).join(
        User, User.id == AttendanceCorrection.teacher_id,
    ).where(AttendanceCorrection.attendance_id == record.id).order_by(AttendanceCorrection.id)).all() if record else []
    present = bool(db.scalar(select(attendance_active()).where(Attendance.id == record.id))) if record else False
    balance = enrollment_balance(db, enrollment_id)
    version = f"{record.id if record else 0}:{history[-1][0].id if history else 0}:{balance_version(balance)}"
    return dict(lesson=lesson, enrollment=enrollment, student=student, record=record,
                history=history, present=present, balance=balance, version=version,
                legacy=snapshot is None, group=db.get(Group, lesson.group_id))


def correct_attendance(engine, teacher_id, lesson_id, enrollment_id, action, reason, expected_version, *, request=None):
    reason = reason.strip()
    if action not in ('present', 'reverse') or not 1 <= len(reason) <= 500:
        raise ValueError('Choose a valid action and enter a reason of 1–500 characters.')
    with write_transaction(engine) as db:
        if request is not None:
            actor = current_user(request, db)
            if actor is None or actor.id != teacher_id:
                raise HTTPException(303, headers={'Location': '/login'})
        teacher = db.get(User, teacher_id)
        if teacher is None or teacher.role != 'teacher':
            raise HTTPException(403, 'Only a teacher can correct attendance.')
        context = correction_context(db, lesson_id, enrollment_id)
        if context['version'] != expected_version:
            raise ValueError('Attendance or balance changed. Review the updated preview before confirming again.')
        if (action == 'present') == context['present']:
            raise ValueError('Attendance already has that status. No balance change was made.')
        record = context['record']
        if record is None:
            packages = context['balance']['packages']
            if not packages:
                raise ValueError('This enrollment needs an initial lesson package first.')
            package = next((p for p in packages if p['remaining'] > 0), packages[-1])
            record = Attendance(lesson_id=lesson_id, enrollment_id=enrollment_id, package_id=package['id'])
            db.add(record)
            db.flush()
            event_action = 'manual'
        else:
            event_action = 'restore' if action == 'present' else 'reverse'
        db.add(AttendanceCorrection(attendance_id=record.id, teacher_id=teacher_id,
                                    action=event_action, reason=reason))
        # Effective attendance determines the debit. No destructive edits, counter
        # overwrites or duplicate compensating balance adjustments are needed.


def review_page(request, db, user, lesson_id, enrollment_id, error=None, reason=''):
    context = correction_context(db, lesson_id, enrollment_id)
    return render(request, 'correct_attendance.html', 400 if error else 200,
                  user=user, error=error, reason=reason[:500], **context)


@router.get('/{lesson_id}/enrollments/{enrollment_id}/attendance', response_class=HTMLResponse)
def review(lesson_id: int, enrollment_id: int, request: Request,
           db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    return review_page(request, db, user, lesson_id, enrollment_id)


@router.post('/{lesson_id}/enrollments/{enrollment_id}/attendance', response_class=HTMLResponse)
def save(lesson_id: int, enrollment_id: int, request: Request,
         action: str = Form(default=''), reason: str = Form(default=''),
         expected_version: str = Form(default=''), csrf: str = Form(default=''),
         db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    verify_csrf(request, csrf)
    try:
        correct_attendance(request.app.state.database_engine, user.id, lesson_id, enrollment_id,
                           action, reason, expected_version, request=request)
    except ValueError as error:
        return review_page(request, db, user, lesson_id, enrollment_id, str(error), reason)
    return RedirectResponse(f'/teacher/lessons/{lesson_id}', status_code=303)
