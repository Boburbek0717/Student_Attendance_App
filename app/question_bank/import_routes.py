from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException
from app.models import User
from app.teacher import require_teacher
from app.security import verify_csrf
from app.web import get_db, render
from app.question_bank.pdf_import import MAX_PDF, parse_pdf, inspect_review, commit_review

router = APIRouter(prefix='/teacher/questions/import')


@router.get('')
def upload_page(request: Request, user: User = Depends(require_teacher)):
    return render(request, 'question_import.html', user=user, error=None)


@router.post('')
async def upload(request: Request, db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    try:
        async with request.form(max_files=1, max_fields=2, max_part_size=16384) as form:
            verify_csrf(request, str(form.get('csrf', '')))
            document = form.get('pdf')
            if not isinstance(document, UploadFile):
                raise ValueError('Choose a PDF to upload.')
            payload = await document.read(MAX_PDF + 1)
            name = (document.filename or 'Question import.pdf').replace('\\', '/').split('/')[-1][:200]
            data = await run_in_threadpool(parse_pdf, payload, request.app.state.pdf_reviews)
            data['source_name'] = name
        db.rollback()
        user = require_teacher(request, db)
        token = request.app.state.pdf_reviews.put((user.id, request.session.get('session_id')), data)
        return RedirectResponse(f'/teacher/questions/import/{token}', 303)
    except ValueError as error:
        return render(request, 'question_import.html', 400, user=user, error=str(error))


@router.get('/{token}')
def review(token: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require_teacher)):
    store = request.app.state.pdf_reviews
    try:
        with store.lock:
            entry = store.get(token, (user.id, request.session.get('session_id')))
            rows, problems = inspect_review(db, entry['data'])
            return render(request, 'question_import_review.html', user=user, token=token,
                data=entry['data'], rows=rows, problems=problems, result=entry['result'],
                notice=request.session.pop('import_notice', None),
                duplicates=sum(row['duplicate'] for row in rows))
    except ValueError as error:
        raise HTTPException(404, str(error)) from None


@router.post('/{token}')
def confirm(token: str, request: Request, mode: str = Form(default=''), csrf: str = Form(default=''),
            user: User = Depends(require_teacher)):
    verify_csrf(request, csrf)
    try:
        commit_review(request.app.state.database_engine, request, request.app.state.pdf_reviews, token, mode)
    except ValueError as error:
        request.session['import_notice'] = str(error)
    return RedirectResponse(f'/teacher/questions/import/{token}', 303)
