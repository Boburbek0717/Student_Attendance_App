from app.question_bank.media import image_view
"""Group assignments with pinned revisions and independent, append-only attempts."""
import re
from contextlib import contextmanager
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException
from app.database import write_transaction
from app.models import Group, Enrollment, User, utc_now
from app.school_time import SCHOOL_ZONE
from app.teacher import require_teacher
from app.security import verify_csrf
from app.web import get_db, render
from app.question_bank.practice import require_access
from app.question_bank.submission_limits import limit_new_answer
from app.question_bank.models import (Assignment, AssignmentItem, AssignmentRecipient,
    AssignmentAttempt, Question, Revision, Choice, AnswerKey, Skill)

router = APIRouter()


@contextmanager
def assignment_write(engine):
    try:
        with write_transaction(engine) as db:
            yield db
    except ValueError:
        # Transaction helper has already rolled back. Do not expose database details.
        raise HTTPException(503, 'Could not save right now. Go back and retry your submission.',
                            headers={'Retry-After': '2'}) from None



def student_assignment(db, request, assignment_id):
    user = require_access(request, db)
    assignment = db.get(Assignment, assignment_id) if 0 < assignment_id < 2**63 else None
    if not assignment or not db.get(AssignmentRecipient, (assignment_id, user.id)):
        raise HTTPException(404, 'Assignment not available.')
    return user, assignment


def items_for(db, assignment_id):
    return db.execute(select(AssignmentItem, Revision).join(Revision,
        AssignmentItem.revision_id == Revision.id).where(AssignmentItem.assignment_id == assignment_id)
        .order_by(AssignmentItem.position)).all()


def progress(db, assignment, user):
    rows = items_for(db, assignment.id)
    attempts = db.scalars(select(AssignmentAttempt).where(AssignmentAttempt.assignment_id == assignment.id,
        AssignmentAttempt.student_id == user.id).order_by(AssignmentAttempt.number)).all()
    return summarize_progress(assignment, rows, attempts)


def progress_many(db, assignments, user):
    """Fetch list progress in two queries, regardless of assignment count."""
    if not assignments:
        return []
    ids = [assignment.id for assignment in assignments]
    rows_by_assignment = {}
    for item, revision in db.execute(select(AssignmentItem, Revision).join(Revision,
            AssignmentItem.revision_id == Revision.id).where(AssignmentItem.assignment_id.in_(ids))
            .order_by(AssignmentItem.position)):
        rows_by_assignment.setdefault(item.assignment_id, []).append((item, revision))
    attempts_by_assignment = {}
    for attempt in db.scalars(select(AssignmentAttempt).where(
            AssignmentAttempt.assignment_id.in_(ids), AssignmentAttempt.student_id == user.id)
            .order_by(AssignmentAttempt.number)):
        attempts_by_assignment.setdefault(attempt.assignment_id, []).append(attempt)
    return [summarize_progress(assignment, rows_by_assignment.get(assignment.id, []),
            attempts_by_assignment.get(assignment.id, [])) for assignment in assignments]


def summarize_progress(assignment, rows, attempts):
    states = {}
    for attempt in attempts:
        old = states.get(attempt.item_id)
        if old in ('correct', 'retried'): continue
        states[attempt.item_id] = ('correct' if attempt.number == 1 else 'retried') if attempt.is_correct else 'incorrect'
    done = len(states)
    completed = bool(rows) and done == len(rows)
    # Deadline completion is based on the first submission of every item, not later retries.
    first_dates = [a.created_at for a in attempts if a.number == 1]
    late = bool(assignment.due_at and (max(first_dates) if completed else utc_now()) > assignment.due_at)
    next_item = next((item for item, _ in rows if item.id not in states), rows[0][0] if rows else None)
    return dict(assignment=assignment, rows=rows, states=states, done=done, total=len(rows),
        state='Completed' if completed else 'In progress' if done else 'To do', late=late, next_item=next_item,
        completed_at=max(first_dates) if completed else None,
        last_activity=max((a.created_at for a in attempts), default=None))


@router.get('/teacher/assignments')
def teacher_list(request: Request, db: Session = Depends(get_db)):
    user = require_teacher(request, db)
    rows = db.execute(select(Assignment, Group.name, func.count(AssignmentRecipient.student_id))
        .join(Group, Assignment.group_id == Group.id)
        .join(AssignmentRecipient, AssignmentRecipient.assignment_id == Assignment.id)
        .where(Assignment.created_by == user.id).group_by(Assignment.id, Group.name)
        .order_by(Assignment.id.desc()).limit(100)).all()
    return render(request, 'assignment_teacher.html', user=user, assignments=rows)


@router.get('/teacher/assignments/new')
def new_assignment(request: Request, db: Session = Depends(get_db)):
    user = require_teacher(request, db)
    return assignment_form(request, db, user)


def assignment_form(request, db, user, *, values=None, error=None, status_code=200):
    values = values or {}
    rows = db.execute(select(Question, Revision, Skill).join(Revision,
        Question.published_revision_id == Revision.id).join(Skill, Revision.skill_id == Skill.id)
        .where(Question.status == 'published', Revision.question_type == 'multiple_choice', Revision.media_id.is_(None))
        .order_by(Skill.name, Question.id)).all()
    selected = set(values.get('questions', []))
    available = {f'{q.id}:{r.id}' for q, r, skill in rows}
    removed = len(selected - available)
    return render(request, 'assignment_new.html', status_code, user=user, rows=rows,
        groups=db.scalars(select(Group).order_by(Group.name)).all(),
        submission_key=values.get('submission_key') or secrets.token_urlsafe(32),
        values=values, selected=selected & available, removed=removed, error=error)


@router.get('/teacher/assignments/{assignment_id}')
def teacher_report(assignment_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_teacher(request, db)
    assignment = db.get(Assignment, assignment_id) if 0 < assignment_id < 2**63 else None
    if not assignment or assignment.created_by != user.id:
        raise HTTPException(404, 'Assignment not available.')
    rows = items_for(db, assignment.id)
    recipients = db.scalars(select(User).join(AssignmentRecipient,
        AssignmentRecipient.student_id == User.id).where(
        AssignmentRecipient.assignment_id == assignment.id).order_by(User.display_name, User.id)).all()
    attempts_by_student = {}
    for attempt in db.scalars(select(AssignmentAttempt).where(
            AssignmentAttempt.assignment_id == assignment.id).order_by(AssignmentAttempt.number)):
        attempts_by_student.setdefault(attempt.student_id, []).append(attempt)
    reports = []
    for student in recipients:
        report = summarize_progress(assignment, rows, attempts_by_student.get(student.id, []))
        report['student'] = student
        report['results'] = {state: sum(value == state for value in report['states'].values())
                             for state in ('correct', 'retried', 'incorrect')}
        reports.append(report)
    return render(request, 'assignment_report.html', user=user, assignment=assignment,
        group=db.get(Group, assignment.group_id), reports=reports,
        completed=sum(report['state'] == 'Completed' for report in reports))


@router.post('/teacher/assignments/new')
def create_assignment(request: Request, title: str = Form(''), instructions: str = Form(''),
        group_id: int = Form(0), due: str = Form(''), questions: list[str] = Form([]),
        submission_key: str = Form(''), csrf: str = Form('')):
    verify_csrf(request, csrf)
    with Session(request.app.state.database_engine) as db:
        require_teacher(request, db)
    values = dict(title=title, instructions=instructions, group_id=group_id, due=due,
                  questions=questions, submission_key=submission_key)
    try:
        return save_assignment(request, title, instructions, group_id, due, questions, submission_key)
    except HTTPException as error:
        if error.status_code not in (400, 409, 503):
            raise
        if not re.fullmatch(r'[A-Za-z0-9_-]{32,64}', submission_key):
            values['submission_key'] = secrets.token_urlsafe(32)
        with Session(request.app.state.database_engine) as db:
            user = require_teacher(request, db)
            response = assignment_form(request, db, user, values=values,
                error=error.detail, status_code=error.status_code)
            if error.headers:
                response.headers.update(error.headers)
            return response


def save_assignment(request, title, instructions, group_id, due, questions, submission_key):
    title, instructions = title.strip(), instructions.strip()
    if not title or len(title) > 120 or len(instructions) > 2000 or '\x00' in title + instructions:
        raise HTTPException(400, 'Enter a title (up to 120 characters) and instructions up to 2000 characters.')
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,64}', submission_key): raise HTTPException(400, 'Reload the assignment form.')
    due_at = None
    if due:
        try:
            local = datetime.strptime(due, '%Y-%m-%dT%H:%M')
            due_at = local.replace(tzinfo=SCHOOL_ZONE).astimezone(timezone.utc).replace(tzinfo=None)
        except (ValueError, OverflowError): raise HTTPException(400, 'Choose a valid due date and time.') from None
    if not 1 <= len(questions) <= 50 or len(set(questions)) != len(questions):
        raise HTTPException(400, 'Select between 1 and 50 different questions.')
    with assignment_write(request.app.state.database_engine) as db:
        user = require_teacher(request, db)
        previous = db.scalar(select(Assignment).where(Assignment.submission_key == submission_key))
        if previous:
            if previous.created_by != user.id: raise HTTPException(409, 'Reload the assignment form.')
            return RedirectResponse('/teacher/assignments', 303)
        if not 0 < group_id < 2**63 or not db.get(Group, group_id): raise HTTPException(400, 'Choose an available group.')
        students = db.scalars(select(Enrollment.student_id).join(User, Enrollment.student_id==User.id)
            .where(Enrollment.group_id == group_id, Enrollment.active.is_(True), User.role=='student')).all()
        if not students: raise HTTPException(400, 'This group has no active students. Enroll students before assigning work.')
        revisions = []
        for value in questions:
            try:
                qid, rid = map(int, value.split(':'))
                if not (0 < qid < 2**63 and 0 < rid < 2**63): raise ValueError()
            except ValueError: raise HTTPException(400, 'Invalid question selection.') from None
            q, revision = db.get(Question, qid), db.get(Revision, rid)
            if not q or q.status != 'published' or q.published_revision_id != rid or not revision or not revision.sealed or revision.question_type != 'multiple_choice' or revision.media_id:
                raise HTTPException(409, 'A selected question changed. Reload and review the selection before assigning.')
            if rid in revisions:
                raise HTTPException(400, 'Select each question only once.')
            revisions.append(rid)
        assignment = Assignment(title=title, instructions=instructions, group_id=group_id,
            due_at=due_at, created_by=user.id, submission_key=submission_key)
        db.add(assignment); db.flush()
        db.add_all([AssignmentRecipient(assignment_id=assignment.id, student_id=s) for s in students])
        db.add_all([AssignmentItem(assignment_id=assignment.id, revision_id=r, position=i+1) for i,r in enumerate(revisions)])
    return RedirectResponse('/teacher/assignments',303)


@router.get('/student/assignments')
def student_list(request: Request, db: Session = Depends(get_db)):
    user = require_access(request, db)
    assignments = db.scalars(select(Assignment).join(AssignmentRecipient,
        AssignmentRecipient.assignment_id == Assignment.id).where(AssignmentRecipient.student_id == user.id)
        .order_by(Assignment.id.desc()).limit(100)).all()
    return render(request, 'assignment_list.html', user=user, cards=progress_many(db, assignments, user))


@router.get('/student/assignments/{assignment_id}')
def overview(assignment_id: int, request: Request, db: Session = Depends(get_db)):
    user, assignment = student_assignment(db, request, assignment_id)
    return render(request, 'assignment_overview.html', user=user, **progress(db,assignment,user))


def assigned_item(db, request, assignment_id, item_id):
    user, assignment = student_assignment(db, request, assignment_id)
    item = db.get(AssignmentItem, item_id) if 0 < item_id < 2**63 else None
    if not item or item.assignment_id != assignment.id: raise HTTPException(404, 'Question not in this assignment.')
    return user, assignment, item


@router.get('/student/assignments/{assignment_id}/questions/{item_id}')
def question(assignment_id: int, item_id: int, request: Request, retry: bool = False, db: Session = Depends(get_db)):
    return question_page(db, request, assignment_id, item_id, retry=retry)


def question_page(db, request, assignment_id, item_id, *, retry=False, error=None,
                  status_code=200, retry_key=None, selected_choice=None):
    user, assignment, item = assigned_item(db,request,assignment_id,item_id)
    revision = db.get(Revision,item.revision_id)
    attempt = None if retry else db.scalar(select(AssignmentAttempt).where(AssignmentAttempt.item_id==item.id,
        AssignmentAttempt.student_id==user.id).order_by(AssignmentAttempt.number.desc()).limit(1))
    reveal = attempt and (attempt.is_correct or attempt.number >= 2)
    choices = db.scalars(select(Choice).where(Choice.revision_id==revision.id).order_by(Choice.position)).all()
    fresh = attempt is not None and request.session.pop('assignment_feedback',None) == attempt.id
    return render(request,'assignment_question.html',status_code,user=user,assignment=assignment,item=item,
        content=dict(id=revision.id,stem=revision.stem,passage=revision.passage,difficulty=revision.difficulty, image=image_view(db, revision)),
        choices=choices,attempt=attempt,answer=db.get(AnswerKey,revision.id) if reveal else None,
        explanation=revision.explanation if reveal else None,fresh_feedback=fresh,
        error=error, selected_choice=selected_choice, retry_key=retry_key or secrets.token_urlsafe(32),
        items=items_for(db,assignment.id))


@router.post('/student/assignments/{assignment_id}/questions/{item_id}/answer')
def submit_answer(assignment_id: int,item_id: int,request: Request,choice_id: int=Form(0),
        retry_key: str=Form(''),csrf: str=Form('')):
    verify_csrf(request,csrf)
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,64}',retry_key): raise HTTPException(400,'Reload the question before answering.')
    try:
        return save_answer(assignment_id, item_id, request, choice_id, retry_key)
    except HTTPException as error:
        if error.status_code not in (400, 429, 503):
            raise
        # The write context has rolled back. Recheck access before showing content.
        with Session(request.app.state.database_engine) as db:
            message = error.detail
            if error.status_code == 503:
                message = 'Could not save right now. Your selection is kept below. Wait a moment, then check your answer again.'
            elif error.status_code == 429:
                message = ('You have submitted answers too quickly. This answer was not saved. '
                           f'Wait {error.headers["Retry-After"]} seconds, then check your answer again. '
                           'Your selection is kept below; previously saved answers are safe.')
            response = question_page(db, request, assignment_id, item_id, retry=True,
                error=message, status_code=error.status_code, retry_key=retry_key, selected_choice=choice_id)
            response.headers.update(error.headers or {})
            return response


def save_answer(assignment_id, item_id, request, choice_id, retry_key):
    with assignment_write(request.app.state.database_engine) as db:
        user, assignment, item = assigned_item(db,request,assignment_id,item_id)
        choice = db.get(Choice,choice_id) if 0 < choice_id < 2**63 else None
        if not choice or choice.revision_id != item.revision_id: raise HTTPException(400,'Choose one of the listed answers.')
        attempt = db.scalar(select(AssignmentAttempt).where(AssignmentAttempt.student_id==user.id,AssignmentAttempt.submission_key==retry_key))
        if attempt:
            if attempt.item_id!=item.id or attempt.choice_id!=choice_id: raise HTTPException(409,'This submission was already used. Reload the question.')
        else:
            limit_new_answer(db, user.id)
            number = (db.scalar(select(func.max(AssignmentAttempt.number)).where(AssignmentAttempt.student_id==user.id,AssignmentAttempt.item_id==item.id)) or 0)+1
            key=db.get(AnswerKey,item.revision_id)
            attempt=AssignmentAttempt(assignment_id=assignment.id,item_id=item.id,revision_id=item.revision_id,
                student_id=user.id,choice_id=choice_id,number=number,is_correct=key.choice_id==choice_id,submission_key=retry_key)
            db.add(attempt);db.flush()
        request.session['assignment_feedback']=attempt.id
    return RedirectResponse(f'/student/assignments/{assignment_id}/questions/{item_id}',303)
