"""Authenticated practice; correctness and answer disclosure stay on the server."""
import re
import secrets
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException
from app.database import write_transaction
from app.models import Enrollment, User
from app.student import require_student
from app.security import verify_csrf
from app.web import get_db, render
from app.question_bank.models import Question, Revision, Choice, AnswerKey, Attempt, Bookmark, Skill, Domain, Section, Bank

router = APIRouter(prefix='/student/questions')


def require_access(request, db):
    user = require_student(request, db)
    if not db.scalar(select(Enrollment.id).where(Enrollment.student_id == user.id, Enrollment.active.is_(True)).limit(1)):
        raise HTTPException(403, 'Question practice requires an active enrollment. Ask your teacher to check your enrollment.')
    return user


def published(db, question_id):
    q = db.get(Question, question_id) if 0 < question_id < 2**63 else None
    if not q or q.status != 'published': raise HTTPException(404, 'Question not available.')
    return q


@router.get('')
def library(request: Request, page: int = 1, db: Session = Depends(get_db)):
    user = require_access(request, db)
    if not 1 <= page <= 100000: raise HTTPException(400, 'Invalid page.')
    rows = db.execute(select(Question, Revision).join(Revision, Question.published_revision_id == Revision.id)
        .where(Question.status == 'published').order_by(Question.id).offset((page-1)*20).limit(21)).all()
    return render(request, 'practice_library.html', user=user, rows=rows[:20], more=len(rows)>20, page=page)


def question_page(request, db, user, question_id, attempt_id=None, error=None, retry_key=None):
    q = published(db, question_id)
    attempt = None
    if attempt_id is not None:
        attempt = db.get(Attempt, attempt_id) if 0 < attempt_id < 2**63 else None
        if not attempt or attempt.student_id != user.id or attempt.question_id != q.id:
            raise HTTPException(404, 'Attempt not found.')
    revision = db.get(Revision, attempt.revision_id if attempt else q.published_revision_id)
    # Explicit public projection: the full revision/key never enter pre-answer HTML.
    content = dict(id=revision.id, stem=revision.stem, passage=revision.passage, difficulty=revision.difficulty)
    taxonomy=db.execute(select(Bank.name,Section.name,Skill.name).select_from(Skill)
        .join(Domain,Skill.domain_id==Domain.id).join(Section,Domain.section_id==Section.id)
        .join(Bank,Section.bank_id==Bank.id).where(Skill.id==revision.skill_id)).one()
    choices = db.scalars(select(Choice).where(Choice.revision_id == revision.id).order_by(Choice.position)).all()
    key = db.get(AnswerKey, revision.id) if attempt else None
    previous = db.scalar(select(Question.id).where(Question.status=='published', Question.id<q.id).order_by(Question.id.desc()).limit(1))
    following = db.scalar(select(Question.id).where(Question.status=='published', Question.id>q.id).order_by(Question.id).limit(1))
    return render(request, 'practice_question.html', 400 if error else 200, user=user, question=q,
        content=content, taxonomy=taxonomy, choices=choices, attempt=attempt, answer=key,
        explanation=revision.explanation if attempt else None, previous=previous, following=following,
        error=error, retry_key=retry_key or secrets.token_urlsafe(32),
        saved=db.get(Bookmark,(user.id,q.id)) is not None)


@router.get('/{question_id}')
def show(question_id: int, request: Request, attempt: int | None = None, retry: bool = False, db: Session = Depends(get_db)):
    user = require_access(request, db)
    if attempt is None and not retry:
        q=published(db,question_id)
        attempt=db.scalar(select(Attempt.id).where(Attempt.student_id==user.id,Attempt.question_id==q.id,
            Attempt.revision_id==q.published_revision_id).order_by(Attempt.number.desc()).limit(1))
    return question_page(request, db, user, question_id, attempt)


def record_answer(engine, request, question_id, revision_id, choice_id, retry_key):
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,64}',retry_key):
        raise ValueError('This form expired. Reload the question before answering.')
    with write_transaction(engine) as db:
        user = require_access(request, db)
        existing = db.scalar(select(Attempt).where(Attempt.student_id==user.id, Attempt.submission_key==retry_key))
        if existing:
            if (existing.question_id,existing.revision_id,existing.choice_id)!=(question_id,revision_id,choice_id):
                raise ValueError('This submission was already used. Open the question again.')
            return existing.id
        q = published(db, question_id)
        if q.published_revision_id != revision_id:
            raise ValueError('This question changed. Reload it before answering.')
        revision = db.get(Revision, revision_id)
        if revision.question_type != 'multiple_choice': raise ValueError('This question type is not available yet.')
        choice = db.get(Choice, choice_id) if 0 < choice_id < 2**63 else None
        if not choice or choice.revision_id != revision_id: raise ValueError('Choose one of the listed answers.')
        key = db.get(AnswerKey, revision_id)
        number = (db.scalar(select(func.max(Attempt.number)).where(Attempt.student_id==user.id,Attempt.question_id==q.id)) or 0)+1
        attempt = Attempt(student_id=user.id,question_id=q.id,revision_id=revision_id,choice_id=choice.id,
            is_correct=choice.id==key.choice_id,number=number,submission_key=retry_key)
        db.add(attempt); db.flush()
        return attempt.id


@router.post('/{question_id}/answer')
def answer(question_id: int, request: Request, revision_id: int = Form(default=0), choice_id: int = Form(default=0),
           retry_key: str = Form(default=''), csrf: str = Form(default=''), db: Session = Depends(get_db)):
    user = require_access(request, db); verify_csrf(request,csrf)
    try:
        attempt_id = record_answer(request.app.state.database_engine,request,question_id,revision_id,choice_id,retry_key)
    except ValueError as error:
        db.expire_all()
        return question_page(request,db,user,question_id,error=str(error),retry_key=retry_key)
    return RedirectResponse(f'/student/questions/{question_id}?attempt={attempt_id}',303)


@router.post('/{question_id}/bookmark')
def bookmark(question_id: int, request: Request, saved: str = Form(default=''), csrf: str = Form(default='')):
    verify_csrf(request,csrf)
    with write_transaction(request.app.state.database_engine) as db:
        user=require_access(request,db); published(db,question_id)
        item=db.get(Bookmark,(user.id,question_id))
        if saved=='yes' and not item: db.add(Bookmark(student_id=user.id,question_id=question_id))
        elif saved=='no' and item: db.delete(item)
        elif saved not in ('yes','no'): raise HTTPException(400,'Invalid bookmark action.')
    return RedirectResponse(f'/student/questions/{question_id}',303)
