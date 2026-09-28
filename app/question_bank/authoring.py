"""Teacher draft authoring. No publication or student answer serialization."""
import hashlib
import json
import secrets

from sqlalchemy import select
from starlette.exceptions import HTTPException

from app.database import write_transaction
from app.models import utc_now
from app.teacher import require_teacher
from app.question_bank.models import Question, Revision, Choice, AnswerKey, Skill, Source, Domain

FIELDS = {'stem': 2000, 'passage': 4000, 'explanation': 2000,
          'source_name': 200, 'rights_note': 600, 'source_reference': 200}


class DraftError(ValueError):
    def __init__(self, message, field='stem'):
        super().__init__(message)
        self.field = field


def question_or_404(db, question_id):
    question = db.get(Question, question_id) if 0 < question_id < 2**63 else None
    if question is None:
        raise HTTPException(404, 'Question not found.')
    return question


def validate(values):
    clean = {name: str(values.get(name, '')).strip() for name in FIELDS}
    for name, maximum in FIELDS.items():
        if len(clean[name]) > maximum:
            raise DraftError(f'Use at most {maximum} characters in this field.', name)
        if '\x00' in clean[name]:
            raise DraftError('Remove unsupported null characters.', name)
    if not clean['stem']:
        raise DraftError('Enter the question text.')
    if values.get('skill_id') == 'new':
        name = ' '.join(str(values.get('new_category_name', '')).split())
        if not name or len(name) > 200 or any(ord(c) < 32 for c in name):
            raise DraftError('Enter a category name using 1–200 characters.', 'new_category_name')
        try:
            domain_id = int(values.get('new_category_domain', ''))
            if not 0 < domain_id < 2**63: raise ValueError()
        except (ValueError, TypeError):
            raise DraftError('Choose the assessment and subject area for your new category.', 'new_category_domain') from None
        clean.update(skill_id=None, new_category_name=name, new_category_domain=domain_id)
    else:
        try:
            clean['skill_id'] = int(values.get('skill_id', ''))
            if not 0 < clean['skill_id'] < 2**63: raise ValueError()
        except (ValueError, TypeError):
            raise DraftError('Choose a category.', 'skill_id') from None
    clean['difficulty'] = values.get('difficulty', '')
    if clean['difficulty'] not in ('easy', 'medium', 'hard'):
        raise DraftError('Choose a difficulty.', 'difficulty')
    if any(str(values.get(f'choice_{i}', '')).strip() for i in (4, 5)):
        raise DraftError('Use only four answer choices: A, B, C and D.', 'choice_0')
    clean['choices'] = [str(values.get(f'choice_{i}', '')).strip() for i in range(4)]
    for i, choice in enumerate(clean['choices']):
        if len(choice) > 600 or '\x00' in choice:
            raise DraftError('Use at most 600 characters and no null characters.', f'choice_{i}')
    answer = values.get('answer', '')
    if answer not in ('', '0', '1', '2', '3'):
        raise DraftError('Choose a valid correct answer.', 'answer')
    if answer and not clean['choices'][int(answer)]:
        raise DraftError('The correct answer must have answer text.', 'answer')
    clean['answer'] = answer
    return clean


def save_draft(engine, request, values, question_id=None, expected_revision=''):
    clean = validate(values)
    with write_transaction(engine) as db:
        # Recheck the actual session after acquiring the write lock, not just its role
        # from the earlier route dependency (a reset may revoke it meanwhile).
        teacher = require_teacher(request, db)
        if clean['skill_id'] is None:
            domain_id = clean.pop('new_category_domain')
            name = clean.pop('new_category_name')
            if db.get(Domain, domain_id) is None:
                raise DraftError('Choose an available subject area.', 'new_category_domain')
            # The write lock also serializes duplicate category creation/retries.
            existing = db.scalars(select(Skill).where(Skill.domain_id == domain_id)).all()
            category = next((item for item in existing if ' '.join(item.name.split()).casefold() == name.casefold()), None)
            if category is None:
                category = Skill(domain_id=domain_id, name=name, code='custom-' + secrets.token_hex(16))
                db.add(category)
                db.flush()
            clean['skill_id'] = category.id
        if db.get(Skill, clean['skill_id']) is None:
            raise DraftError('Choose an available category.', 'skill_id')
        digest = hashlib.sha256(json.dumps(clean, sort_keys=True).encode()).hexdigest()
        if question_id is None:
            question = Question(created_by=teacher.id)
            db.add(question)
            db.flush()
            number = 1
        else:
            question = question_or_404(db, question_id)
            if question.status != 'draft':
                raise DraftError('Only drafts can be edited in this release. Return to the library.')
            if str(question.current_revision_id) != expected_revision:
                raise DraftError('A newer revision was saved. Your text is kept below; open the latest preview before copying your changes into a fresh editor.')
            previous = db.get(Revision, question.current_revision_id)
            if db.scalar(select(Choice.id).where(Choice.revision_id == previous.id, Choice.position >= 4).limit(1)):
                raise DraftError('This older question has more than four choices and cannot be edited here.')
            if previous.question_type != 'multiple_choice' or previous.media_id:
                raise DraftError('This editor cannot safely edit this question type or attached media.')
            if previous.content_hash == digest:
                return question.id
            number = previous.number + 1
        source_id = None
        if clean['source_name'] or clean['rights_note']:
            source = Source(name=clean['source_name'], rights_note=clean['rights_note'], created_by=teacher.id)
            db.add(source)
            db.flush()
            source_id = source.id
        revision = Revision(question_id=question.id, number=number,
            skill_id=clean['skill_id'], difficulty=clean['difficulty'],
            stem=clean['stem'], passage=clean['passage'], explanation=clean['explanation'],
            source_id=source_id, source_reference=clean['source_reference'],
            content_hash=digest, created_by=teacher.id)
        db.add(revision)
        db.flush()
        for i, value in enumerate(clean['choices']):
            if value:
                choice = Choice(revision_id=revision.id, position=i, text=value)
                db.add(choice)
                db.flush()
                if clean['answer'] == str(i):
                    db.add(AnswerKey(revision_id=revision.id, choice_id=choice.id))
        db.flush()
        # Complete drafts can be sealed now; incomplete work remains saveable.
        revision.sealed = bool(clean['answer'] and all(clean['choices']))
        question.current_revision_id = revision.id
        question.updated_at = utc_now()
        return question.id


def editor_values(db, revision):
    values = {name: getattr(revision, name, '') for name in FIELDS}
    values.update(skill_id=str(revision.skill_id), difficulty=revision.difficulty, answer='')
    key = db.get(AnswerKey, revision.id)
    for choice in db.scalars(select(Choice).where(Choice.revision_id == revision.id)):
        values[f'choice_{choice.position}'] = choice.text
        if key and key.choice_id == choice.id:
            values['answer'] = str(choice.position)
    if revision.source_id:
        source = db.get(Source, revision.source_id)
        values.update(source_name=source.name, rights_note=source.rights_note)
    return values
