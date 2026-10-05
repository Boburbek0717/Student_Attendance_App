import secrets
import re
from datetime import date, timezone
from app.database import write_transaction
from app.school_time import SCHOOL_ZONE
from app.school_time import school_time

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from app.attendance import check_in, student_records
from app.models import User, StudentGoal, utc_now
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


def dashboard(request: Request, db: Session, user: User, error=None, status_code=None, retry_key=None, goal_error=None, goal_values=None):
    from sqlalchemy import select
    from app.question_bank.models import Assignment, AssignmentRecipient
    assignments = db.scalars(select(Assignment).join(AssignmentRecipient,
        AssignmentRecipient.assignment_id == Assignment.id).where(AssignmentRecipient.student_id == user.id)
        .order_by(Assignment.id.desc()).limit(3)).all()
    goal = db.get(StudentGoal, user.id)
    today = utc_now().replace(tzinfo=timezone.utc).astimezone(SCHOOL_ZONE).date()
    days_left = (goal.exam_date - today).days if goal and goal.exam_date else None
    return render(request, "student.html", status_code or (400 if error else 200), user=user, error=error, assignments=assignments,
                  goal=goal, days_left=days_left, goal_error=goal_error,
                  goal_values=goal_values if goal_values is not None else dict(
                      target_score=goal.target_score if goal and goal.target_score else '',
                      exam_date=goal.exam_date.isoformat() if goal and goal.exam_date else '',
                      version=goal.version if goal else 0),
                  goal_notice=request.session.pop("goal_notice", None),
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


@router.post("/goal", response_class=HTMLResponse)
def save_goal(request: Request, target_score: str = Form(''), exam_date: str = Form(''),
              version: str = Form(''), csrf: str = Form(''), db: Session = Depends(get_db),
              user: User = Depends(require_student)):
    verify_csrf(request, csrf)
    values = dict(target_score=target_score, exam_date=exam_date, version=version)
    try:
        if target_score and (not re.fullmatch(r'[0-9]{3,4}', target_score)
                or not 400 <= int(target_score) <= 1600 or int(target_score) % 10):
            raise ValueError('Choose a target score from 400 to 1600, in steps of 10.')
        if not re.fullmatch(r'[0-9]{1,10}', version):
            raise ValueError('Reload the dashboard before saving your goal.')
        chosen_date = None
        if exam_date:
            try:
                if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', exam_date):
                    raise ValueError()
                chosen_date = date.fromisoformat(exam_date)
            except ValueError:
                raise ValueError('Enter a valid exam date.') from None
        with write_transaction(request.app.state.database_engine) as tx:
            current = require_student(request, tx)
            goal = tx.get(StudentGoal, current.id)
            if int(version) != (goal.version if goal else 0):
                raise HTTPException(409, 'Your goal changed in another tab. Reload the dashboard to see the latest goal before editing.')
            if goal is None:
                goal = StudentGoal(student_id=current.id, version=1)
                tx.add(goal)
            else:
                goal.version += 1
            goal.target_score = int(target_score) if target_score else None
            goal.exam_date = chosen_date
    except ValueError as error:
        db.expire_all()
        return dashboard(request, db, user, goal_error=str(error), goal_values=values, status_code=400)
    request.session['goal_notice'] = 'Your SAT goal has been saved.'
    return RedirectResponse('/student#sat-goal', status_code=303)
