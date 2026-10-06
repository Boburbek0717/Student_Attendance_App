"""Authenticated practice; correctness and answer disclosure stay on the server."""
import re
import secrets
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException
from app.database import write_transaction
from app.models import Enrollment, User
from app.student import require_student
from app.security import verify_csrf
from app.web import get_db, render
from app.question_bank.models import Question, Revision, Choice, AnswerKey, Attempt, Bookmark, Skill, Domain, Section, Bank
from app.question_bank.submission_limits import limit_new_answer

router = APIRouter(prefix='/student/questions')


def practice_statuses(db, student_id, rows):
    """Summarize only this student's attempts on the displayed revisions."""
    revision_ids = [revision.id for _, revision in rows]
    if not revision_ids:
        return {}
    results = db.execute(select(Attempt.revision_id, func.min(Attempt.number),
        func.min(case((Attempt.is_correct.is_(True), Attempt.number))))
        .where(Attempt.student_id == student_id, Attempt.revision_id.in_(revision_ids))
        .group_by(Attempt.revision_id)).all()
    return {revision: ('incorrect' if correct is None else
            'correct' if correct == first else 'retried')
            for revision, first, correct in results}


def require_access(request, db):
    user = require_student(request, db)
    if not db.scalar(select(Enrollment.id).where(Enrollment.student_id == user.id, Enrollment.active.is_(True)).limit(1)):
        raise HTTPException(403, 'Question practice requires an active enrollment. Ask your teacher to check your enrollment.')
    return user


def published(db, question_id):
    q = db.get(Question, question_id) if 0 < question_id < 2**63 else None
    if not q or q.status != 'published': raise HTTPException(404, 'Question not available.')
    return q


def theme_query():
    return (select(Skill.id, Skill.name, Bank.name.label('bank'), Section.name.label('section'),
                   func.count(Question.id).label('count'))
        .select_from(Question).join(Revision, Question.published_revision_id == Revision.id)
        .join(Skill, Revision.skill_id == Skill.id).join(Domain, Skill.domain_id == Domain.id)
        .join(Section, Domain.section_id == Section.id).join(Bank, Section.bank_id == Bank.id)
        .where(Question.status == 'published')
        .group_by(Skill.id, Skill.name, Bank.name, Section.name))


@router.get('')
def library(request: Request, db: Session = Depends(get_db)):
    user = require_access(request, db)
    themes = db.execute(theme_query().order_by(Bank.name, Section.name, Skill.name, Skill.id)).all()
    return render(request, 'practice_themes.html', user=user, themes=themes)


@router.get('/themes/{skill_id}')
def theme_library(skill_id: int, request: Request, page: int = 1, db: Session = Depends(get_db)):
    user = require_access(request, db)
    if not 1 <= page <= 100000: raise HTTPException(400, 'Invalid page.')
    theme = db.execute(theme_query().where(Skill.id == skill_id)).first() if 0 < skill_id < 2**63 else None
    if not theme: raise HTTPException(404, 'This theme has no available questions.')
    rows = db.execute(select(Question, Revision).join(Revision, Question.published_revision_id == Revision.id)
        .where(Question.status == 'published', Revision.skill_id == skill_id)
        .order_by(Question.id).offset((page-1)*20).limit(21)).all()
    return render(request, 'practice_library.html', user=user, theme=theme,
                  rows=rows[:20], more=len(rows)>20, page=page,
                  grid_rows=rows[:20], grid_offset=(page-1)*20,
                  statuses=practice_statuses(db, user.id, rows[:20]))


def question_page(request, db, user, question_id, attempt_id=None, error=None, retry_key=None, fresh_feedback=False, guest_result=None, public_mode=False):
    q = published(db, question_id)
    attempt = guest_result if public_mode else None
    if attempt_id is not None:
        attempt = db.get(Attempt, attempt_id) if 0 < attempt_id < 2**63 else None
        if not attempt or attempt.student_id != user.id or attempt.question_id != q.id:
            raise HTTPException(404, 'Attempt not found.')
    revision = db.get(Revision, attempt.revision_id if attempt and not public_mode else q.published_revision_id)
    # Explicit public projection: the full revision/key never enter pre-answer HTML.
    content = dict(id=revision.id, stem=revision.stem, passage=revision.passage, difficulty=revision.difficulty)
    taxonomy=db.execute(select(Bank.name,Section.name,Skill.name).select_from(Skill)
        .join(Domain,Skill.domain_id==Domain.id).join(Section,Domain.section_id==Section.id)
        .join(Bank,Section.bank_id==Bank.id).where(Skill.id==revision.skill_id)).one()
    choices = db.scalars(select(Choice).where(Choice.revision_id == revision.id).order_by(Choice.position)).all()
    # Count saved submissions for this revision, not the question's lifetime
    # attempt number. A newly published revision gets its own first try.
    reveal_answer = False
    if attempt and public_mode:
        reveal_answer = attempt.is_correct or attempt.number >= 2
    elif attempt:
        revision_attempts = db.scalar(select(func.count()).select_from(Attempt).where(
            Attempt.student_id == user.id, Attempt.revision_id == revision.id,
            Attempt.number <= attempt.number))
        reveal_answer = attempt.is_correct or revision_attempts >= 2
    key = db.get(AnswerKey, revision.id) if reveal_answer else None
    # Navigation follows the currently published theme, even when viewing an older attempt.
    current_revision = db.get(Revision, q.published_revision_id)
    theme = db.get(Skill, current_revision.skill_id)
    neighbors = (select(Question.id).join(Revision, Question.published_revision_id == Revision.id)
        .where(Question.status == 'published', Revision.skill_id == theme.id))
    previous = db.scalar(neighbors.where(Question.id < q.id).order_by(Question.id.desc()).limit(1))
    following = db.scalar(neighbors.where(Question.id > q.id).order_by(Question.id).limit(1))
    position = db.scalar(select(func.count()).select_from(Question).join(Revision,
        Question.published_revision_id == Revision.id).where(Question.status == 'published',
        Revision.skill_id == theme.id, Question.id < q.id))
    grid_offset = (position // 20) * 20
    grid_rows = db.execute(select(Question, Revision).join(Revision,
        Question.published_revision_id == Revision.id).where(Question.status == 'published',
        Revision.skill_id == theme.id).order_by(Question.id).offset(grid_offset).limit(20)).all()
    return render(request, 'practice_question.html', 400 if error else 200, user=user, question=q,
        grid_rows=grid_rows, grid_offset=grid_offset, statuses={} if public_mode else practice_statuses(db, user.id, grid_rows),
        public_mode=public_mode, practice_root="/questions" if public_mode else "/student/questions",
        content=content, taxonomy=taxonomy, theme=theme, fresh_feedback=fresh_feedback, choices=choices, attempt=attempt, answer=key,
        explanation=revision.explanation if reveal_answer else None, previous=previous, following=following,
        error=error, retry_key=retry_key or secrets.token_urlsafe(32),
        saved=False if public_mode else db.get(Bookmark,(user.id,q.id)) is not None)


@router.get('/{question_id}')
def show(question_id: int, request: Request, attempt: int | None = None, retry: bool = False, db: Session = Depends(get_db)):
    user = require_access(request, db)
    if attempt is None and not retry:
        q=published(db,question_id)
        attempt=db.scalar(select(Attempt.id).where(Attempt.student_id==user.id,Attempt.question_id==q.id,
            Attempt.revision_id==q.published_revision_id).order_by(Attempt.number.desc()).limit(1))
    fresh = attempt is not None and request.session.get('practice_feedback') == attempt
    if fresh:
        request.session.pop('practice_feedback', None)
    return question_page(request, db, user, question_id, attempt, fresh_feedback=fresh)


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
        limit_new_answer(db, user.id)
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
    request.session['practice_feedback'] = attempt_id
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
