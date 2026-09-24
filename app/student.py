import secrets
from app.school_time import school_time

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from app.attendance import check_in, student_records
from app.models import User
from app.security import current_user, verify_csrf, limit_attendance_attempt
from app.web import get_db, render


router = APIRouter(prefix="/student")


def require_student(request: Request, db: Session = Depends(get_db)) -> User:
    user = current_user(request, db)
    if user is None:
        raise HTTPException(303, headers={"Location": "/login"})
    if user.role != "student":
        raise HTTPException(403, "Your account cannot open this page.")
    return user


def dashboard(request: Request, db: Session, user: User, error=None, status_code=None, retry_key=None):
    return render(request, "student.html", status_code or (400 if error else 200), user=user, error=error,
                  retry_key=retry_key or secrets.token_urlsafe(32),
                  notice=request.session.pop("attendance_notice", None),
                  **student_records(db, user.id))


@router.get("", response_class=HTMLResponse)
def student_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_student)):
    return dashboard(request, db, user)


@router.post("/check-in", response_class=HTMLResponse)
def submit_attendance(
    request: Request, code: str = Form(default=""), csrf: str = Form(default=""),
    retry_key: str = Form(default=""),
    db: Session = Depends(get_db), user: User = Depends(require_student),
):
    verify_csrf(request, csrf)
    try:
        limit_attendance_attempt(request.app.state.database_engine, user.id)
        result = check_in(request.app.state.database_engine, user.id, code, request=request, retry_key=retry_key or secrets.token_urlsafe(32))
    except HTTPException as error:
        if error.status_code != 429:
            raise
        response = dashboard(request, db, user, error=f"Too many attempts. Try again in {error.headers['Retry-After']} seconds. Your attendance history below shows any saved check-in.", status_code=429, retry_key=retry_key)
        response.headers["Retry-After"] = error.headers["Retry-After"]
        return response
    except ValueError as error:
        return dashboard(request, db, user, error=str(error), retry_key=retry_key)
    balance = result["balance"]
    message = "Already checked in. No extra lesson was used." if result["already"] else "Attendance recorded. One lesson has been used from your package."
    request.session["attendance_notice"] = (
        f"{message} {result['group']} · Lesson #{result['lesson_id']} · {school_time(result['started_at'])}."
        + (f" You now have {-balance} lesson(s) owed. Your teacher can record a renewal." if balance < 0 else "")
    )
    return RedirectResponse("/student", status_code=303)
