"""Public practice: published content only, no course-record writes."""
import re
import time
from threading import Lock
from types import SimpleNamespace
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException
from app.security import current_user, verify_csrf
from app.models import Enrollment
from app.web import get_db, render
from app.question_bank.models import Question, Revision, Choice, AnswerKey, Skill, Bank, Section
from app.question_bank.practice import theme_query, published, question_page


class GuestLimiter:
    """Bounded per-process IP budget; never trust request forwarding headers here."""
    def __init__(self):
        self.lock = Lock()
        self.buckets = {}

    def check(self, address, write):
        now = time.monotonic()
        with self.lock:
            self.buckets = {k: v for k, v in self.buckets.items() if now - v[0] < 60}
            key = (address, write)
            start, count = self.buckets.get(key, (now, 0))
            if count >= (30 if write else 240) or (key not in self.buckets and len(self.buckets) >= 10000):
                raise HTTPException(429, 'Too many practice requests. Wait a minute and try again.', headers={'Retry-After': '60'})
            self.buckets[key] = (start, count + 1)


def limit(request: Request):
    request.app.state.guest_limiter.check(request.client.host if request.client else 'unknown', request.method == 'POST')


router = APIRouter(prefix='/questions', dependencies=[Depends(limit)])


def member_redirect(request, db, suffix=''):
    user = current_user(request, db)
    if user and user.role == 'student' and db.scalar(select(Enrollment.id).where(
        Enrollment.student_id == user.id, Enrollment.active.is_(True)).limit(1)):
        return RedirectResponse('/student/questions' + suffix, 303)


@router.get('')
def library(request: Request, db: Session = Depends(get_db)):
    redirect = member_redirect(request, db)
    if redirect: return redirect
    themes = db.execute(theme_query().order_by(Bank.name, Section.name, Skill.name, Skill.id)).all()
    return render(request, 'practice_themes.html', user=None, themes=themes, public_mode=True, practice_root='/questions')


@router.get('/themes/{skill_id}')
def theme(skill_id: int, request: Request, page: int = 1, db: Session = Depends(get_db)):
    if not 1 <= page <= 100000: raise HTTPException(400, 'Invalid page.')
    redirect = member_redirect(request, db, f'/themes/{skill_id}?page={page}')
    if redirect: return redirect
    selected = db.execute(theme_query().where(Skill.id == skill_id)).first() if 0 < skill_id < 2**63 else None
    if not selected: raise HTTPException(404, 'This theme has no available questions.')
    rows = db.execute(select(Question, Revision).join(Revision, Question.published_revision_id == Revision.id)
        .where(Question.status == 'published', Revision.skill_id == skill_id).order_by(Question.id)
        .offset((page-1)*20).limit(21)).all()
    return render(request, 'practice_library.html', user=None, theme=selected, rows=rows[:20], more=len(rows)>20,
        page=page, grid_rows=rows[:20], grid_offset=(page-1)*20, statuses={}, public_mode=True, practice_root='/questions')


def result_for(request, question):
    result = request.session.get('guest_answers', {}).get(str(question.id))
    return result if result and result['revision'] == question.published_revision_id else None


def show_result(request, db, question_id, result=None, error=None):
    attempt = SimpleNamespace(choice_id=result['choice'], number=result['number'], is_correct=result['correct']) if result else None
    return question_page(request, db, None, question_id, public_mode=True, guest_result=attempt,
        retry_key=result['key'] if result else None, error=error, fresh_feedback=False)


@router.get('/{question_id}')
def show(question_id: int, request: Request, retry: bool = False, db: Session = Depends(get_db)):
    redirect = member_redirect(request, db, f'/{question_id}' + ('?retry=1' if retry else ''))
    if redirect: return redirect
    q = published(db, question_id)
    return show_result(request, db, question_id, None if retry else result_for(request, q))


@router.post('/{question_id}/answer')
def answer(question_id: int, request: Request, revision_id: int = Form(default=0), choice_id: int = Form(default=0),
           retry_key: str = Form(default=''), csrf: str = Form(default=''), db: Session = Depends(get_db)):
    verify_csrf(request, csrf)
    q = published(db, question_id)
    if q.published_revision_id != revision_id:
        return show_result(request, db, question_id, error='This question changed. Reload it before answering.')
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,64}', retry_key):
        return show_result(request, db, question_id, error='This form expired. Reload the question.')
    choice = db.get(Choice, choice_id) if 0 < choice_id < 2**63 else None
    if not choice or choice.revision_id != revision_id:
        return show_result(request, db, question_id, error='Choose one of the listed answers.')
    previous = result_for(request, q)
    if previous and previous['key'] == retry_key:
        if previous['choice'] != choice_id: raise HTTPException(409, 'This answer was already checked. Start another attempt.')
        return RedirectResponse(f'/questions/{question_id}', 303)
    key = db.get(AnswerKey, revision_id)
    answers = request.session.get('guest_answers', {})
    answers.pop(str(question_id), None)
    answers[str(question_id)] = dict(revision=revision_id, choice=choice_id, key=retry_key,
        number=min(2, previous['number']+1) if previous else 1, correct=choice_id == key.choice_id)
    # Keep the signed cookie small. Long-term guest progress lives only in the browser.
    request.session['guest_answers'] = dict(list(answers.items())[-6:])
    return RedirectResponse(f'/questions/{question_id}', 303)
