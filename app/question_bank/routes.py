from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException
from starlette.concurrency import run_in_threadpool

from app.models import User, utc_now
from app.database import write_transaction
from app.question_bank.models import PublicationEvent
from app.question_bank.publication import publish_revision
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
def library(request: Request, page: int = 1, theme_id: int | None = None,
            db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    if not 1 <= page <= 100000:
        raise HTTPException(400, 'Choose a valid library page.')
    themes_query = (select(Skill.id, Skill.name, Bank.name.label('bank'),
        Section.name.label('section'), func.count(Question.id).label('count'),
        func.sum(case((Question.status == 'published', 1), else_=0)).label('published'))
        .select_from(Question).join(Revision, Question.current_revision_id == Revision.id)
        .join(Skill, Revision.skill_id == Skill.id).join(Domain, Skill.domain_id == Domain.id)
        .join(Section, Domain.section_id == Section.id).join(Bank, Section.bank_id == Bank.id)
        .group_by(Skill.id, Skill.name, Bank.name, Section.name))
    if theme_id is None:
        themes = db.execute(themes_query.order_by(Bank.name, Section.name, Skill.name, Skill.id)).all()
        return render(request, 'question_themes.html', user=user, themes=themes)
    theme = db.execute(themes_query.where(Skill.id == theme_id)).first() if 0 < theme_id < 2**63 else None
    if not theme:
        raise HTTPException(404, 'Question category not found.')
    rows = db.execute(select(Question, Revision).join(Revision, Question.current_revision_id == Revision.id)
        .where(Revision.skill_id == theme_id)
        .order_by(Question.id.desc()).offset((page-1)*20).limit(21)).all()
    return render(request, 'question_library.html', user=user, theme=theme,
                  rows=rows[:20], page=page, more=len(rows)>20)


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
        history=history, duplicate=duplicate, saved=request.query_params.get('saved') == '1',
        publication_version=db.scalar(select(func.max(PublicationEvent.id)).where(PublicationEvent.question_id==question.id)) or 0,
        publication_notice=request.session.pop('publication_notice',None))


@router.post('/{question_id}/publication')
def publication(question_id: int, request: Request, action: str=Form(default=''),
                revision_id: int=Form(default=0), version: int=Form(default=-1), csrf: str=Form(default='')):
    verify_csrf(request,csrf)
    try:
        with write_transaction(request.app.state.database_engine) as db:
            teacher=require_teacher(request,db)
            question=question_or_404(db,question_id)
            current_version=db.scalar(select(func.max(PublicationEvent.id)).where(PublicationEvent.question_id==question.id)) or 0
            if current_version!=version or question.current_revision_id!=revision_id:
                raise ValueError('Question state changed. Review the latest preview before trying again.')
            if action=='publish': publish_revision(db,teacher.id,question_id,revision_id)
            elif action in ('unpublish','archive'):
                desired='draft' if action=='unpublish' else 'archived'
                if question.status=='archived': raise ValueError('This question is already archived.')
                if question.status!=desired:
                    question.status=desired;question.published_revision_id=None;question.updated_at=utc_now()
                    db.add(PublicationEvent(question_id=question.id,revision_id=revision_id,teacher_id=teacher.id,action=action))
            else: raise ValueError('Invalid publication action.')
        request.session['publication_notice']='Question publication status updated.'
    except ValueError as error:
        request.session['publication_notice']=str(error)
    return RedirectResponse(f'/teacher/questions/{question_id}/preview',303)
