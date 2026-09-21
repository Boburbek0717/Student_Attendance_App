from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from app.create_user import create_user
from app.models import Attendance, Enrollment, Group, LessonPackage, User
from app.security import current_user, verify_csrf
from app.web import get_db, render


router = APIRouter(prefix="/teacher")
NOTICES = {
    "group": "Group created. You can now enroll students.",
    "student": "Student account created. You can now enroll the student in a group.",
    "enrollment": "Student enrolled with a new 12-lesson package.",
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
        .outerjoin(Attendance, Attendance.package_id == LessonPackage.id)
        .group_by(LessonPackage.id)
        .order_by(LessonPackage.purchased_at, LessonPackage.id)
    ).all()
    packages_by_enrollment = {}
    for package, used in packages:
        packages_by_enrollment.setdefault(package.enrollment_id, []).append({
            "id": package.id, "limit": package.lesson_limit,
            "used": used, "remaining": package.lesson_limit - used,
        })
    members_by_group = {}
    for enrollment, student in memberships:
        members_by_group.setdefault(enrollment.group_id, []).append({
            "student": student, "active": enrollment.active,
            "packages": packages_by_enrollment.get(enrollment.id, []),
        })
    return render(
        request, "teacher.html", 400 if error else 200, user=user,
        groups=groups, students=students, members_by_group=members_by_group,
        error=error, section=section, values=values or {},
        notice=NOTICES.get(request.query_params.get("created")) if not error else None,
    )


@router.get("", response_class=HTMLResponse)
def teacher_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    return dashboard(request, db, user)


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
