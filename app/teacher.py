from app.attendance_state import attendance_active, attendance_origin, correction_version
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from app.create_user import create_user
from app.attendance import start_lesson, student_records
from app.packages import package_balance, enrollment_balance, renew_package
from app.models import LessonClosure, Attendance, BalanceAdjustment, Enrollment, Group, Lesson, LessonPackage, User, utc_now
from app.security import current_user, verify_csrf
from app.web import get_db, render


router = APIRouter(prefix="/teacher")
NOTICES = {
    "group": "Group created. You can now enroll students.",
    "student": "Student account created. You can now enroll the student in a group.",
    "enrollment": "Student enrolled with a new 12-lesson package.",
    "renewal": "Renewal recorded: 12 lessons added. Any lessons owed were covered first.",
}


def require_teacher(request: Request, db: Session = Depends(get_db)) -> User:
    user = current_user(request, db)
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Your account cannot open this page.")
    return user


def dashboard(request: Request, db: Session, user: User, *, error=None, section=None, values=None):
    groups = db.scalars(select(Group).order_by(Group.name, Group.id)).all()
    students = db.scalars(select(User).where(User.role == "student").order_by(User.display_name, User.id)).all()
    memberships = db.execute(
        select(Enrollment, User).join(User, User.id == Enrollment.student_id)
        .order_by(User.display_name, Enrollment.id)
    ).all()
    packages = db.execute(
        select(LessonPackage, func.count(Attendance.id))
        .outerjoin(Attendance, (Attendance.package_id == LessonPackage.id) & attendance_active())
        .group_by(LessonPackage.id)
        .order_by(LessonPackage.purchased_at, LessonPackage.id)
    ).all()
    rows_by_enrollment = {}
    for package, used in packages:
        rows_by_enrollment.setdefault(package.enrollment_id, []).append((package, used))
    adjustments_by_enrollment = {}
    for adjustment in db.scalars(select(BalanceAdjustment)).all():
        adjustments_by_enrollment.setdefault(adjustment.enrollment_id, []).append(adjustment)
    members_by_group = {}
    for enrollment, student in memberships:
        balance = package_balance(rows_by_enrollment.get(enrollment.id, []), adjustments_by_enrollment.get(enrollment.id, []))
        members_by_group.setdefault(enrollment.group_id, []).append({
            "student": student, "active": enrollment.active, "enrollment_id": enrollment.id,
            "packages": balance["packages"], "balance": balance,
        })
    now = utc_now()
    # One latest started lesson per group, including expired and closed windows.
    ranked = select(Lesson.id.label("id"), func.row_number().over(
        partition_by=Lesson.group_id,
        order_by=(Lesson.started_at.desc(), Lesson.id.desc()),
    ).label("position")).where(Lesson.started_at <= now).subquery()
    recent_lessons = {lesson.group_id: lesson for lesson in db.scalars(
        select(Lesson).join(ranked, ranked.c.id == Lesson.id).where(ranked.c.position == 1)
    ).all()}
    open_lessons = db.scalars(select(Lesson).where(
        Lesson.started_at <= now, Lesson.code_expires_at > now,
    ).order_by(Lesson.id)).all()
    active_lessons = {lesson.group_id: lesson for lesson in open_lessons}
    return render(
        request, "teacher.html", 400 if error else 200, user=user,
        groups=groups, students=students, members_by_group=members_by_group,
        error=error, section=section, values=values or {},
        notice=NOTICES.get(request.query_params.get("created")) if not error else None,
        closures={row.lesson_id: row for row in db.scalars(select(LessonClosure)).all()}, active_lessons=active_lessons, recent_lessons=recent_lessons, now=now, code_minutes=request.app.state.code_minutes,
    )


@router.get("", response_class=HTMLResponse)
def teacher_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    return dashboard(request, db, user)


def renewal_page(request: Request, db: Session, user: User, enrollment_id: int, error=None):
    enrollment = db.get(Enrollment, enrollment_id) if 0 < enrollment_id < 2**63 else None
    if enrollment is None:
        raise HTTPException(404, "Enrollment not found.")
    student = db.get(User, enrollment.student_id)
    group = db.get(Group, enrollment.group_id)
    balance = enrollment_balance(db, enrollment.id)
    after = balance["balance"] + 12
    return render(request, "renew_package.html", 400 if error else 200, user=user,
                  enrollment=enrollment, student=student, group=group, balance=balance,
                  after_available=max(0, after), after_owed=max(0, -after), error=error)


@router.get("/enrollments/{enrollment_id}/renew", response_class=HTMLResponse)
def review_renewal(enrollment_id: int, request: Request, db: Session = Depends(get_db),
                   user: User = Depends(require_teacher)):
    return renewal_page(request, db, user, enrollment_id)


@router.post("/enrollments/{enrollment_id}/renew", response_class=HTMLResponse)
def record_renewal(
    enrollment_id: int, request: Request, csrf: str = Form(default=""),
    expected_package_id: str = Form(default=""), expected_attended: str = Form(default=""),
    expected_adjustment_id: str = Form(default="0"), expected_correction_id: str = Form(default="0"),
    db: Session = Depends(get_db), user: User = Depends(require_teacher),
):
    verify_csrf(request, csrf)
    try:
        try:
            package_id, attended = int(expected_package_id), int(expected_attended)
            adjustment_id = int(expected_adjustment_id)
            correction_id = int(expected_correction_id)
            if package_id < 0 or attended < 0 or adjustment_id < 0 or correction_id < 0:
                raise ValueError
        except ValueError:
            raise ValueError("Reload the renewal page and review the balance before confirming.") from None
        renew_package(request.app.state.database_engine, user.id, enrollment_id, package_id, attended, adjustment_id, correction_id)
    except ValueError as error:
        return renewal_page(request, db, user, enrollment_id, error=str(error))
    return RedirectResponse("/teacher?created=renewal#groups", status_code=303)


@router.post("/groups/{group_id}/lessons", response_class=HTMLResponse)
def start_group_lesson(
    group_id: int, request: Request, csrf: str = Form(default=""),
    db: Session = Depends(get_db), user: User = Depends(require_teacher),
):
    verify_csrf(request, csrf)
    try:
        start_lesson(request.app.state.database_engine, user.id, group_id, request.app.state.code_minutes)
    except ValueError as error:
        return dashboard(request, db, user, error=str(error), section="lesson")
    return RedirectResponse(f"/teacher#group-{group_id}", status_code=303)


@router.get("/students/{student_id}/history", response_class=HTMLResponse)
def student_history(
    student_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_teacher),
):
    student = db.get(User, student_id) if 0 < student_id < 2**63 else None
    if student is None or student.role != "student":
        raise HTTPException(404, "Student not found.")
    return render(request, "student_history.html", user=user, student=student,
                  **student_records(db, student.id))


@router.post("/groups", response_class=HTMLResponse)
def create_group(
    request: Request, group_name: str = Form(default=""), csrf: str = Form(default=""),
    db: Session = Depends(get_db), user: User = Depends(require_teacher),
):
    verify_csrf(request, csrf)
    name = group_name.strip()
    if not 1 <= len(name) <= 100:
        return dashboard(request, db, user, error="Enter a group name of 1–100 characters.",
                         section="group", values={"group_name": group_name[:100]})
    db.add(Group(name=name))
    db.commit()
    return RedirectResponse("/teacher?created=group#groups", status_code=303)


@router.post("/students", response_class=HTMLResponse)
def create_student(
    request: Request, username: str = Form(default=""), display_name: str = Form(default=""),
    password: str = Form(default=""), confirm_password: str = Form(default=""),
    csrf: str = Form(default=""), db: Session = Depends(get_db), user: User = Depends(require_teacher),
):
    verify_csrf(request, csrf)
    try:
        if password != confirm_password:
            raise ValueError("The passwords do not match. Enter them again.")
        create_user(db, username, display_name, password, role="student")
    except ValueError as error:
        return dashboard(request, db, user, error=str(error), section="student",
                         values={"username": username[:100], "display_name": display_name[:100]})
    return RedirectResponse("/teacher?created=student#enroll", status_code=303)


def enroll_student(db: Session, student_id: str, group_id: str) -> None:
    try:
        student_key, group_key = int(student_id), int(group_id)
        if not (0 < student_key < 2**63 and 0 < group_key < 2**63):
            raise ValueError
    except ValueError:
        raise ValueError("Choose a valid student and group.") from None
    student = db.get(User, student_key)
    group = db.get(Group, group_key)
    if student is None or student.role != "student" or group is None:
        raise ValueError("Choose an existing student and group.")
    membership = db.scalar(select(Enrollment).where(
        Enrollment.student_id == student_key, Enrollment.group_id == group_key,
    ))
    if membership is not None:
        raise ValueError("This student already has an enrollment in that group. No package was added.")
    enrollment = Enrollment(student_id=student_key, group_id=group_key)
    db.add(enrollment)
    try:
        # Flush obtains the enrollment ID without saving either record yet.
        db.flush()
        db.add(LessonPackage(enrollment_id=enrollment.id, lesson_limit=12))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Enrollment could not be saved. Refresh and check whether it already exists.") from None


@router.post("/enrollments", response_class=HTMLResponse)
def create_enrollment(
    request: Request, student_id: str = Form(default=""), group_id: str = Form(default=""),
    csrf: str = Form(default=""), db: Session = Depends(get_db), user: User = Depends(require_teacher),
):
    verify_csrf(request, csrf)
    try:
        enroll_student(db, student_id, group_id)
    except ValueError as error:
        return dashboard(request, db, user, error=str(error), section="enrollment",
                         values={"student_id": student_id, "group_id": group_id})
    return RedirectResponse("/teacher?created=enrollment#groups", status_code=303)
