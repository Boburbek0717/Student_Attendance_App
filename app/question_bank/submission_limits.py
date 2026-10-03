"""Bound new saved answers per student across practice and assignments."""
from datetime import timedelta
from math import ceil

from sqlalchemy import select
from starlette.exceptions import HTTPException

from app.models import utc_now
from app.question_bank.models import Attempt, AssignmentAttempt

ANSWER_LIMIT = 30
WINDOW_SECONDS = 60


def limit_new_answer(db, student_id):
    """Call inside the answer's BEGIN IMMEDIATE, after idempotency/validation.

    Immutable saved attempts are the persisted budget: restarts cannot reset it,
    and rolled-back writes never consume it. No separate counter can drift.
    """
    now = utc_now()
    cutoff = now - timedelta(seconds=WINDOW_SECONDS)
    recent = []
    for model in (Attempt, AssignmentAttempt):
        recent.extend(db.scalars(select(model.created_at).where(
            model.student_id == student_id, model.created_at > cutoff)
            .order_by(model.created_at.desc()).limit(ANSWER_LIMIT)).all())
    if len(recent) >= ANSWER_LIMIT:
        oldest_counted = sorted(recent, reverse=True)[ANSWER_LIMIT - 1]
        retry = max(1, ceil((oldest_counted + timedelta(seconds=WINDOW_SECONDS) - now).total_seconds()))
        raise HTTPException(429,
            f'You have submitted answers too quickly. This answer was not saved. '
            f'Wait {retry} seconds, then go back to the question and submit again. '
            'Your previously saved answers are safe.',
            headers={'Retry-After': str(retry)})
