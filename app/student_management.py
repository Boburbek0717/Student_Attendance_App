from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from app.attendance import student_records
from app.database import write_transaction
from app.models import Enrollment, LoginSession, User
from app.security import normalize_username, password_hasher, verify_csrf
from app.teacher import require_teacher
from app.web import get_db, render


router = APIRouter(prefix="/teacher/students")


def managed_student(db: Session, student_id: int) -> User:
    student = db.get(User, student_id) if 0 < student_id < 2**63 else None
    if student is None or student.role != "student":
        raise HTTPException(404, "Student not found.")
    return student


def check_teacher(db: Session, teacher_id: int) -> None:
    teacher = db.get(User, teacher_id)
    if teacher is None or teacher.role != "teacher":
        raise HTTPException(403, "Only a teacher can manage students.")


def update_profile(engine, teacher_id: int, student_id: int, username: str, display_name: str,
                   expected_username: str, expected_name: str) -> None:
    username = normalize_username(username)
    display_name = display_name.strip()
    if not 1 <= len(display_name) <= 100:
        raise ValueError("The display name must contain 1–100 characters.")
    with write_transaction(engine) as db:
        check_teacher(db, teacher_id)
        student = managed_student(db, student_id)
        if (student.username, student.display_name) != (expected_username, expected_name):
            raise ValueError("This profile changed since you opened it. Review the current details and try again.")
        duplicate = db.scalar(select(User.id).where(User.username == username, User.id != student.id))
        if duplicate is not None:
            raise ValueError("That username is already in use.")
        student.username = username
        student.display_name = display_name


def reset_password(engine, teacher_id: int, student_id: int, password: str, confirmation: str) -> None:
    if password != confirmation:
        raise ValueError("The passwords do not match. Enter them again.")
    if not 12 <= len(password) <= 128:
        raise ValueError("Use a password containing 12–128 characters.")
    hashed = password_hasher.hash(password)
    with write_transaction(engine) as db:
        check_teacher(db, teacher_id)
        student = managed_student(db, student_id)
        student.password_hash = hashed
        db.execute(delete(LoginSession).where(LoginSession.user_id == student.id))


def set_enrollment_active(engine, teacher_id: int, student_id: int, enrollment_id: int, active: bool) -> None:
    with write_transaction(engine) as db:
        check_teacher(db, teacher_id)
        managed_student(db, student_id)
        enrollment = db.get(Enrollment, enrollment_id) if 0 < enrollment_id < 2**63 else None
        if enrollment is None or enrollment.student_id != student_id:
            raise HTTPException(404, "Enrollment not found for this student.")
        # Set an explicit state instead of toggling, so repeated POSTs are harmless.
        enrollment.active = active


def detail_page(request, db, user, student_id, *, error=None, section=None):
    student = managed_student(db, student_id)
    return render(request, "manage_student.html", 400 if error else 200, user=user, student=student,
                  error=error, section=section, notice=request.session.pop("management_notice", None),
                  **student_records(db, student_id))


@router.get("", response_class=HTMLResponse)
def directory(request: Request, q: str = "", db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    query = q.strip()[:100]
    statement = select(User).where(User.role == "student")
    if query:
        statement = statement.where(or_(User.username.contains(query, autoescape=True),
                                        User.display_name.contains(query, autoescape=True)))
    students = db.scalars(statement.order_by(User.display_name, User.id)).all()
    return render(request, "students.html", user=user, students=students, query=query)


@router.get("/{student_id}/manage", response_class=HTMLResponse)
def manage_student(student_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    return detail_page(request, db, user, student_id)


@router.post("/{student_id}/profile", response_class=HTMLResponse)
def save_profile(
    student_id: int, request: Request, username: str = Form(default=""), display_name: str = Form(default=""),
    expected_username: str = Form(default=""), expected_name: str = Form(default=""), csrf: str = Form(default=""),
    db: Session = Depends(get_db), user: User = Depends(require_teacher),
):
    verify_csrf(request, csrf)
    try:
        update_profile(request.app.state.database_engine, user.id, student_id, username, display_name,
                       expected_username, expected_name)
    except ValueError as error:
        return detail_page(request, db, user, student_id, error=str(error), section="profile")
    request.session["management_notice"] = "Student details saved. Tell the student if their username changed."
    return RedirectResponse(f"/teacher/students/{student_id}/manage", status_code=303)


@router.post("/{student_id}/password", response_class=HTMLResponse)
def save_password(
    student_id: int, request: Request, password: str = Form(default=""), confirm_password: str = Form(default=""),
    csrf: str = Form(default=""), db: Session = Depends(get_db), user: User = Depends(require_teacher),
):
    verify_csrf(request, csrf)
    try:
        reset_password(request.app.state.database_engine, user.id, student_id, password, confirm_password)
    except ValueError as error:
        return detail_page(request, db, user, student_id, error=str(error), section="password")
    request.session["management_notice"] = "Password reset. The student's existing logins have been signed out. Share the new password privately."
    return RedirectResponse(f"/teacher/students/{student_id}/manage", status_code=303)


@router.post("/{student_id}/enrollments/{enrollment_id}/status", response_class=HTMLResponse)
def save_enrollment_status(
    student_id: int, enrollment_id: int, request: Request, active: str = Form(default=""), csrf: str = Form(default=""),
    db: Session = Depends(get_db), user: User = Depends(require_teacher),
):
    verify_csrf(request, csrf)
    try:
        if active not in {"true", "false"}:
            raise ValueError("Choose deactivate or reactivate.")
        set_enrollment_active(request.app.state.database_engine, user.id, student_id, enrollment_id, active == "true")
    except ValueError as error:
        return detail_page(request, db, user, student_id, error=str(error), section="enrollment")
    request.session["management_notice"] = (
        "Enrollment reactivated. Existing balances and history are unchanged."
        if active == "true" else "Enrollment deactivated. Check-in is blocked for this group; history and balances are preserved."
    )
    return RedirectResponse(f"/teacher/students/{student_id}/manage#memberships", status_code=303)
