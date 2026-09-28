from sqlalchemy import select, func
from starlette.exceptions import HTTPException
from app.models import User, utc_now
from app.question_bank.models import Question, Revision, Choice, AnswerKey, PublicationEvent


def publish_revision(db, teacher_id, question_id, expected_revision):
    teacher=db.get(User,teacher_id)
    if not teacher or teacher.role!='teacher': raise HTTPException(403,'Teacher access required.')
    question=db.get(Question,question_id) if 0<question_id<2**63 else None
    if not question: raise HTTPException(404,'Question not found.')
    if question.current_revision_id!=expected_revision: raise ValueError('The draft changed. Review its latest revision.')
    revision=db.get(Revision,expected_revision)
    if revision.question_type!='multiple_choice' or revision.media_id:
        raise ValueError('Publish a complete multiple-choice draft without unsupported media.')
    choices = db.scalars(select(Choice).where(Choice.revision_id == revision.id).order_by(Choice.position)).all()
    answer = db.get(AnswerKey, revision.id)
    if ([c.position for c in choices] != [0, 1, 2, 3] or any(not c.text.strip() for c in choices)
            or not answer or answer.choice_id not in {c.id for c in choices}):
        raise ValueError('Fill all four options (A–D) and choose the correct answer before publishing.')
    if not revision.sealed:
        revision.sealed = True
        db.flush()
    if question.status=='archived': raise ValueError('Archived questions cannot be published.')
    if question.status=='published' and question.published_revision_id==revision.id: return
    question.status='published';question.published_revision_id=revision.id;question.updated_at=utc_now()
    db.add(PublicationEvent(question_id=question.id,revision_id=revision.id,action='publish',teacher_id=teacher.id))
