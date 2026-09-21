from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from app.attendance import check_in, student_records
from app.models import User
from app.security import current_user, verify_csrf
from app.web import get_db, render


router = APIRouter(prefix="/student")


def require_student(request: Request, db: Session = Depends(get_db)) -> User:
    user = current_user(request, db)
    if user is None:
        raise HTTPException(303, headers={"Location": "/login"})
    if user.role != "student":
        raise HTTPException(403, "Your account cannot open this page.")
    return user


def dashboard(request: Request, db: Session, user: User, error=None):
    return render(request, "student.html", 400 if error else 200, user=user, error=error,
                  notice=request.session.pop("attendance_notice", None),
                  **student_records(db, user.id))


@router.get("", response_class=HTMLResponse)
def student_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_student)):
    return dashboard(request, db, user)


@router.post("/check-in", response_class=HTMLResponse)
def submit_attendance(
    request: Request, code: str = Form(default=""), csrf: str = Form(default=""),
    db: Session = Depends(get_db), user: User = Depends(require_student),
):
    verify_csrf(request, csrf)
    request.app.state.checkin_limiter.check(str(user.id))
    try:
        check_in(request.app.state.database_engine, user.id, code)
    except ValueError as error:
        return dashboard(request, db, user, error=str(error))
    request.session["attendance_notice"] = "Attendance recorded. One lesson has been used from your package."
    return RedirectResponse("/student", status_code=303)
