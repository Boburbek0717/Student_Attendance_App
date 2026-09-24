from app.attendance_state import attendance_active, attendance_origin, correction_version
from datetime import timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from app.database import write_transaction
from app.attendance import new_attendance_code
from app.models import LessonClosure, AttendanceCorrection, Attendance, Enrollment, Group, Lesson, LessonRoster, LessonRosterSnapshot, User, utc_now
from app.security import current_user, verify_csrf
from app.teacher import require_teacher
from app.web import get_db, render


router = APIRouter(prefix="/teacher")


def find_record(db, model, record_id):
    record = db.get(model, record_id) if 0 < record_id < 2**63 else None
    if record is None:
        raise HTTPException(404, "Lesson or group not found.")
    return record


def code_version(lesson):
    return f"{lesson.attendance_code or ''}:{lesson.code_expires_at.isoformat() if lesson.code_expires_at else ''}"


def change_check_in(engine, teacher_id, lesson_id, expected_version, *, reopen=False, minutes=15):
    with write_transaction(engine) as db:
        teacher = db.get(User, teacher_id)
        if teacher is None or teacher.role != "teacher":
            raise HTTPException(403, "Only a teacher can manage check-in.")
        lesson = find_record(db, Lesson, lesson_id)
        if db.get(LessonClosure, lesson_id):
            raise ValueError("This lesson is permanently finished or cancelled and cannot be reopened.")
        if not reopen and lesson.attendance_code is None:
            return
        if expected_version != code_version(lesson):
            raise ValueError("Check-in changed since you opened this page. Review its current status and try again.")
        if reopen:
            if not 1 <= minutes <= 60:
                raise ValueError("Choose a code duration of 1–60 minutes.")
            now = utc_now()
            if lesson.started_at > now:
                raise ValueError("This lesson has not started yet.")
            active = db.scalar(select(Lesson.id).where(
                Lesson.group_id == lesson.group_id, Lesson.code_expires_at > now,
            ))
            if active is not None:
                raise ValueError("A lesson in this group already has open check-in. Close it before reopening this lesson.")
            lesson.attendance_code = new_attendance_code(db, now, lesson.attendance_code)
            lesson.code_expires_at = now + timedelta(minutes=minutes)
            return
        # Clear both fields together to satisfy the code-window constraint.
        # This is safe to repeat and never changes attendance or packages.
        lesson.attendance_code = None
        lesson.code_expires_at = None


@router.get("/groups/{group_id}/lessons", response_class=HTMLResponse)
def lesson_history(group_id: int, request: Request, page: int = 1,
                   db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    group = find_record(db, Group, group_id)
    count = db.scalar(select(func.count()).select_from(Lesson).where(Lesson.group_id == group_id))
    last_page = max(1, (count + 24) // 25)
    page = max(1, min(page, last_page))
    lessons = db.execute(select(Lesson, func.count(Attendance.id)).outerjoin(
        Attendance, (Attendance.lesson_id == Lesson.id) & attendance_active(),
    ).where(Lesson.group_id == group_id).group_by(Lesson.id)
        .order_by(Lesson.started_at.desc(), Lesson.id.desc()).offset((page - 1) * 25).limit(25)).all()
    absence_counts = {}
    for lesson, _ in lessons:
        snapshot = db.get(LessonRosterSnapshot, lesson.id) is not None
        all_recorded = select(Attendance.enrollment_id).where(Attendance.lesson_id == lesson.id)
        expected = Enrollment.id.in_(select(LessonRoster.enrollment_id).where(LessonRoster.lesson_id == lesson.id)) if snapshot else Enrollment.active.is_(True)
        roster = select(Enrollment.id).where(Enrollment.group_id == group.id, expected | Enrollment.id.in_(all_recorded))
        attended_ids = select(Attendance.enrollment_id).where(Attendance.lesson_id == lesson.id, attendance_active())
        absent = db.scalar(select(func.count()).select_from(roster.where(
            Enrollment.id.not_in(attended_ids),
        ).subquery()))
        absence_counts[lesson.id] = (absent, snapshot)
    return render(request, "lessons.html", user=user, group=group, lessons=lessons,
                  closures={row.lesson_id: row for row in db.scalars(select(LessonClosure)).all()}, absence_counts=absence_counts, now=utc_now(), page=page, last_page=last_page)


def lesson_page(request, db, user, lesson_id, error=None):
    lesson = find_record(db, Lesson, lesson_id)
    group = db.get(Group, lesson.group_id)
    attended = db.execute(select(User, Attendance).join(
        Enrollment, Enrollment.student_id == User.id,
    ).join(Attendance, Attendance.enrollment_id == Enrollment.id)
        .where(Attendance.lesson_id == lesson.id, attendance_active()).order_by(User.display_name, User.id)).all()
    checked_ids = {student.id for student, attendance in attended}
    has_snapshot = db.get(LessonRosterSnapshot, lesson.id) is not None
    roster_query = select(User).join(Enrollment, Enrollment.student_id == User.id)
    if has_snapshot:
        roster_query = roster_query.join(LessonRoster, LessonRoster.enrollment_id == Enrollment.id).where(
            LessonRoster.lesson_id == lesson.id,
        )
    else:
        roster_query = roster_query.where(Enrollment.group_id == group.id, Enrollment.active.is_(True))
    current_students = db.scalars(roster_query.order_by(User.display_name, User.id)).all()
    historical_students = db.scalars(select(User).join(Enrollment, Enrollment.student_id == User.id)
        .join(Attendance, Attendance.enrollment_id == Enrollment.id).where(Attendance.lesson_id == lesson.id)).all()
    current_students = sorted({person.id: person for person in [*current_students, *historical_students]}.values(), key=lambda person: (person.display_name, person.id))
    enrollment_keys = dict(db.execute(select(Enrollment.student_id, Enrollment.id).where(Enrollment.group_id == group.id)).all())
    return render(request, "lesson.html", 400 if error else 200, user=user, lesson=lesson,
                  closure=db.get(LessonClosure, lesson_id), group=group, attended=attended, now=utc_now(), error=error,
                  enrollment_keys=enrollment_keys, has_snapshot=has_snapshot, version=code_version(lesson), code_minutes=request.app.state.code_minutes,
                  missing=[student for student in current_students if student.id not in checked_ids])


@router.get("/lessons/{lesson_id}", response_class=HTMLResponse)
def lesson_detail(lesson_id: int, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_teacher)):
    return lesson_page(request, db, user, lesson_id)


@router.post("/lessons/{lesson_id}/close", response_class=HTMLResponse)
def close_lesson(lesson_id: int, request: Request, csrf: str = Form(default=""),
                 expected_version: str = Form(default=""),
                 db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    verify_csrf(request, csrf)
    try:
        change_check_in(request.app.state.database_engine, user.id, lesson_id, expected_version)
    except ValueError as error:
        return lesson_page(request, db, user, lesson_id, error=str(error))
    return RedirectResponse(f"/teacher/lessons/{lesson_id}", status_code=303)


@router.post("/lessons/{lesson_id}/reopen", response_class=HTMLResponse)
def reopen_lesson(lesson_id: int, request: Request, csrf: str = Form(default=""),
                  expected_version: str = Form(default=""),
                  db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    verify_csrf(request, csrf)
    try:
        change_check_in(request.app.state.database_engine, user.id, lesson_id, expected_version,
                        reopen=True, minutes=request.app.state.code_minutes)
    except ValueError as error:
        return lesson_page(request, db, user, lesson_id, error=str(error))
    return RedirectResponse(f"/teacher/lessons/{lesson_id}", status_code=303)


def closure_version(db, lesson):
    attendance_id = db.scalar(select(func.max(Attendance.id)).where(Attendance.lesson_id == lesson.id)) or 0
    correction_id = db.scalar(select(func.max(AttendanceCorrection.id)).join(
        Attendance, Attendance.id == AttendanceCorrection.attendance_id
    ).where(Attendance.lesson_id == lesson.id)) or 0
    return f"{code_version(lesson)}:{attendance_id}:{correction_id}"


def close_permanently(engine, teacher_id, lesson_id, action, reason, expected_version, request=None):
    if action not in ('finished', 'cancelled') or not 1 <= len(reason.strip()) <= 500:
        raise ValueError("Choose a valid action and enter a reason of 1–500 characters.")
    with write_transaction(engine) as db:
        actor = current_user(request, db) if request is not None else db.get(User, teacher_id)
        if actor is None or actor.id != teacher_id or actor.role != 'teacher':
            raise HTTPException(403, "Only a signed-in teacher can finish a lesson.")
        lesson = find_record(db, Lesson, lesson_id)
        if db.get(LessonClosure, lesson_id):
            raise ValueError("This lesson is already permanently finished or cancelled.")
        if lesson.started_at > utc_now():
            raise ValueError("This lesson has not started yet.")
        if expected_version != closure_version(db, lesson):
            raise ValueError("Lesson attendance or check-in changed. Review the updated preview.")
        if action == 'cancelled' and db.scalar(select(Attendance.id).where(Attendance.lesson_id == lesson_id).limit(1)):
            raise ValueError("Only lessons with no attendance history can be cancelled, even if entries were reversed.")
        # Freeze the documented current-roster fallback for legacy lessons.
        if action == 'finished' and db.get(LessonRosterSnapshot, lesson_id) is None:
            db.add(LessonRosterSnapshot(lesson_id=lesson_id))
            db.flush()
            for enrollment_id in db.scalars(select(Enrollment.id).where(
                Enrollment.group_id == lesson.group_id, Enrollment.active.is_(True)
            )).all():
                db.add(LessonRoster(lesson_id=lesson_id, enrollment_id=enrollment_id))
        lesson.attendance_code = None
        lesson.code_expires_at = None
        db.add(LessonClosure(lesson_id=lesson_id, teacher_id=teacher_id, status=action, reason=reason.strip()))


def closure_preview(request, db, user, lesson_id, error=None):
    lesson = find_record(db, Lesson, lesson_id)
    recorded = db.scalar(select(func.count()).select_from(Attendance).where(Attendance.lesson_id == lesson_id))
    present = db.scalar(select(func.count()).select_from(Attendance).where(Attendance.lesson_id == lesson_id, attendance_active()))
    return render(request, 'finish_lesson.html', 400 if error else 200, user=user,
                  lesson=lesson, group=db.get(Group, lesson.group_id), recorded=recorded,
                  present=present, version=closure_version(db, lesson),
                  legacy=db.get(LessonRosterSnapshot, lesson_id) is None, closure=db.get(LessonClosure, lesson_id), error=error)


@router.get('/lessons/{lesson_id}/finish', response_class=HTMLResponse)
def finish_preview(lesson_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    return closure_preview(request, db, user, lesson_id)


@router.post('/lessons/{lesson_id}/finish', response_class=HTMLResponse)
def finish_save(lesson_id: int, request: Request, action: str = Form(default=''),
                reason: str = Form(default=''), expected_version: str = Form(default=''),
                csrf: str = Form(default=''), db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    verify_csrf(request, csrf)
    try:
        close_permanently(request.app.state.database_engine, user.id, lesson_id,
                          action, reason, expected_version, request)
    except ValueError as error:
        return closure_preview(request, db, user, lesson_id, str(error))
    return RedirectResponse(f'/teacher/lessons/{lesson_id}', status_code=303)
