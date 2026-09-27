from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException
from starlette.concurrency import run_in_threadpool

from app.models import User
from app.security import verify_csrf
from app.teacher import require_teacher
from app.web import get_db, render
from app.question_bank.models import Question, Revision, Choice, AnswerKey, Bank, Section, Domain, Skill, Source
from app.question_bank.authoring import DraftError, FIELDS, editor_values, question_or_404, save_draft

router = APIRouter(prefix='/teacher/questions')


def skills(db):
    return db.execute(select(Skill.id, Skill.name, Domain.name.label('domain'), (Bank.name + ' · ' + Section.name).label('section'))
        .join(Domain, Skill.domain_id == Domain.id).join(Section, Domain.section_id == Section.id)
        .join(Bank, Section.bank_id == Bank.id).order_by(Bank.id, Section.id, Domain.id, Skill.id)).all()


def editor(request, db, user, question=None, values=None, expected='', error=None):
    return render(request, 'question_editor.html', 400 if error else 200,
        user=user, question=question, values=values or {}, expected=expected,
        skills=skills(db), error=str(error) if error else None,
        error_field=getattr(error, 'field', 'stem'), limits=FIELDS)


@router.get('')
def library(request: Request, page: int = 1, db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    if not 1 <= page <= 100000:
        raise HTTPException(400, 'Choose a valid library page.')
    rows = db.execute(select(Question, Revision).join(Revision, Question.current_revision_id == Revision.id)
        .order_by(Question.id.desc()).offset((page-1)*20).limit(21)).all()
    return render(request, 'question_library.html', user=user, rows=rows[:20], page=page, more=len(rows)>20)


@router.get('/new')
def new(request: Request, db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    return editor(request, db, user)


@router.get('/{question_id}/edit')
def edit(question_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    question = question_or_404(db, question_id)
    revision = db.get(Revision, question.current_revision_id)
    if not revision or question.status != 'draft' or revision.question_type != 'multiple_choice' or revision.media_id:
        raise HTTPException(400, 'This question cannot be edited with the draft editor.')
    return editor(request, db, user, question, editor_values(db, revision), str(revision.id))


async def submit(request, db, user, question_id=None):
    form = await request.form()
    verify_csrf(request, str(form.get('csrf', '')))
    names = list(FIELDS) + ['skill_id', 'difficulty', 'answer'] + [f'choice_{i}' for i in range(6)]
    values = {name: str(form.get(name, '')) for name in names}
    expected = str(form.get('expected_revision', ''))
    try:
        saved_id = await run_in_threadpool(save_draft, request.app.state.database_engine, request, values, question_id, expected)
    except ValueError as error:
        db.expire_all()
        question = question_or_404(db, question_id) if question_id else None
        return editor(request, db, user, question, values, expected, error)
    return RedirectResponse(f'/teacher/questions/{saved_id}/preview?saved=1', status_code=303)


@router.post('/new')
async def create(request: Request, db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    return await submit(request, db, user)


@router.post('/{question_id}/edit')
async def update(question_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    return await submit(request, db, user, question_id)


@router.get('/{question_id}/preview')
def preview(question_id: int, request: Request, revision_id: int | None = None,
            db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    question = question_or_404(db, question_id)
    chosen = revision_id if revision_id is not None else question.current_revision_id
    revision = db.get(Revision, chosen) if chosen and 0 < chosen < 2**63 else None
    if revision is None or revision.question_id != question.id:
        raise HTTPException(404, 'Question revision not found.')
    history = db.execute(select(Revision.id, Revision.number, Revision.created_at, User.display_name)
        .join(User, Revision.created_by == User.id).where(Revision.question_id == question.id)
        .order_by(Revision.number.desc()).limit(20)).all()
    duplicate = db.scalar(select(Question.id).join(Revision, Question.current_revision_id == Revision.id)
        .where(Revision.content_hash == revision.content_hash, Question.id != question.id).limit(1))
    taxonomy = db.execute(select(Bank.name, Section.name, Domain.name, Skill.name)
        .select_from(Skill).join(Domain, Skill.domain_id == Domain.id)
        .join(Section, Domain.section_id == Section.id).join(Bank, Section.bank_id == Bank.id)
        .where(Skill.id == revision.skill_id)).one()
    return render(request, 'question_preview.html', user=user, question=question, revision=revision, taxonomy=taxonomy,
        choices=db.scalars(select(Choice).where(Choice.revision_id == revision.id).order_by(Choice.position)).all(),
        answer=db.get(AnswerKey, revision.id), source=db.get(Source, revision.source_id) if revision.source_id else None,
        history=history, duplicate=duplicate, saved=request.query_params.get('saved') == '1')
