"""Bounded raster uploads; revision-aware access, no user-controlled file paths."""
import hashlib
import io
import warnings
from PIL import Image, UnidentifiedImageError
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException
from app.web import get_db
from app.security import current_user
from app.models import Enrollment
from app.question_bank.models import Media, MediaContent, Revision, Question, Attempt, AssignmentItem, AssignmentRecipient

MAX_BYTES = 4 * 1024 * 1024
MAX_PIXELS = 8_000_000
router = APIRouter()


def prepare_image(data, alt):
    from app.question_bank.authoring import DraftError
    if not data or len(data) > MAX_BYTES:
        raise DraftError('Choose a PNG, JPEG or WebP image up to 4 MB.', 'image')
    alt = alt.strip()
    if not alt or len(alt) > 1000 or any(ord(c) < 32 for c in alt):
        raise DraftError('Describe the image in 1–1,000 characters, including graph labels or table values.', 'image_alt')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ('PNG', 'JPEG', 'WEBP') or getattr(image, 'n_frames', 1) != 1:
                    raise ValueError()
                if image.width * image.height > MAX_PIXELS or max(image.size) > 6000:
                    raise ValueError()
                image.load()
                # Fresh raster removes metadata and embedded/non-image payloads.
                clean = Image.new('RGBA' if 'A' in image.getbands() else 'RGB', image.size)
                clean.paste(image.convert(clean.mode))
                output = io.BytesIO()
                clean.save(output, format='PNG')
                encoded = output.getvalue()
                if len(encoded) > MAX_BYTES:
                    raise ValueError()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise DraftError('Use a valid, single-frame PNG, JPEG or WebP, no more than 8 million pixels or 6,000 pixels per side. Try a smaller image.', 'image') from None
    return dict(data=encoded, alt=alt, sha256=hashlib.sha256(encoded).hexdigest())


def image_view(db, revision):
    media = db.get(Media, revision.media_id) if revision.media_id else None
    return dict(url=f'/question-images/{revision.id}', alt=media.alt_text) if media else None


@router.get('/question-images/{revision_id}')
def show_image(revision_id: int, request: Request, db: Session = Depends(get_db)):
    if not 0 < revision_id < 2**63:
        raise HTTPException(404, 'Image not available.')
    revision = db.get(Revision, revision_id)
    if not revision or not revision.media_id:
        raise HTTPException(404, 'Image not available.')
    question = db.get(Question, revision.question_id)
    allowed = question.status == 'published' and question.published_revision_id == revision.id
    if not allowed:
        user = current_user(request, db)
        allowed = bool(user and user.role == 'teacher')
        if user and user.role == 'student' and db.scalar(select(Enrollment.id).where(
                Enrollment.student_id == user.id, Enrollment.active.is_(True)).limit(1)):
            allowed = bool((question.status == 'published' and db.scalar(select(Attempt.id).where(
                Attempt.student_id == user.id, Attempt.revision_id == revision.id).limit(1))) or
                db.scalar(select(AssignmentItem.id).join(AssignmentRecipient,
                    AssignmentRecipient.assignment_id == AssignmentItem.assignment_id).where(
                    AssignmentItem.revision_id == revision.id, AssignmentRecipient.student_id == user.id).limit(1)))
    if not allowed:
        raise HTTPException(404, 'Image not available.')
    content = db.get(MediaContent, revision.media_id)
    if not content:
        raise HTTPException(404, 'Image not available.')
    return Response(content.data, media_type='image/png', headers={
        'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff',
        'Content-Disposition': 'inline; filename="question.png"'})
