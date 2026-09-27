"""Question Bank v1 schema; UTC timestamps, normalized content and activity.

No student serializer should expose Revision.explanation or AnswerKey before a
successful attempt. Role/access and publication validation belong to services.
"""
from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models import utc_now


class SchemaVersion(Base):
    __tablename__ = "qb_schema_versions"
    version: Mapped[int] = mapped_column(primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Bank(Base):
    __tablename__ = "qb_banks"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))


class Section(Base):
    __tablename__ = "qb_sections"
    __table_args__ = (UniqueConstraint("bank_id", "code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("qb_banks.id"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(120))


class Domain(Base):
    __tablename__ = "qb_domains"
    __table_args__ = (UniqueConstraint("section_id", "code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("qb_sections.id"), index=True)
    code: Mapped[str] = mapped_column(String(60))
    name: Mapped[str] = mapped_column(String(160))


class Skill(Base):
    __tablename__ = "qb_skills"
    __table_args__ = (UniqueConstraint("domain_id", "code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("qb_domains.id"), index=True)
    code: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200))


class Source(Base):
    __tablename__ = "qb_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    rights_note: Mapped[str] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Media(Base):
    """Opaque private-storage reference, never a public static URL or raw path."""
    __tablename__ = "qb_media"
    __table_args__ = (CheckConstraint("byte_size > 0"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    storage_key: Mapped[str] = mapped_column(String(100), unique=True)
    mime_type: Mapped[str] = mapped_column(String(80))
    byte_size: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    alt_text: Mapped[str] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Question(Base):
    __tablename__ = "qb_questions"
    __table_args__ = (
        CheckConstraint("status IN ('draft','published','archived')"),
        CheckConstraint("status != 'published' OR published_revision_id IS NOT NULL"),
        ForeignKeyConstraint(["id", "current_revision_id"], ["qb_revisions.question_id", "qb_revisions.id"], deferrable=True, initially="DEFERRED"),
        ForeignKeyConstraint(["id", "published_revision_id"], ["qb_revisions.question_id", "qb_revisions.id"], deferrable=True, initially="DEFERRED"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement="ignore_fk")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    current_revision_id: Mapped[int | None]
    published_revision_id: Mapped[int | None]
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Revision(Base):
    __tablename__ = "qb_revisions"
    __table_args__ = (
        UniqueConstraint("question_id", "number"), UniqueConstraint("question_id", "id"),
        CheckConstraint("number > 0"),
        CheckConstraint("difficulty IN ('easy','medium','hard')"),
        CheckConstraint("question_type IN ('multiple_choice','numeric')"),
        Index("ix_qb_revision_filter", "skill_id", "difficulty"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("qb_questions.id"), index=True)
    number: Mapped[int]
    skill_id: Mapped[int] = mapped_column(ForeignKey("qb_skills.id"))
    difficulty: Mapped[str] = mapped_column(String(10))
    question_type: Mapped[str] = mapped_column(String(30), default="multiple_choice")
    stem: Mapped[str] = mapped_column(Text)
    passage: Mapped[str] = mapped_column(Text, default="")
    explanation: Mapped[str] = mapped_column(Text, default="")
    source_id: Mapped[int | None] = mapped_column(ForeignKey("qb_sources.id"))
    source_reference: Mapped[str] = mapped_column(String(200), default="")
    media_id: Mapped[int | None] = mapped_column(ForeignKey("qb_media.id"))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    sealed: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Choice(Base):
    __tablename__ = "qb_choices"
    __table_args__ = (UniqueConstraint("revision_id", "position"), UniqueConstraint("revision_id", "id"), CheckConstraint("position >= 0"))
    id: Mapped[int] = mapped_column(primary_key=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey("qb_revisions.id"), index=True)
    position: Mapped[int]
    text: Mapped[str] = mapped_column(Text)


class AnswerKey(Base):
    __tablename__ = "qb_answer_keys"
    __table_args__ = (
        ForeignKeyConstraint(["revision_id", "choice_id"], ["qb_choices.revision_id", "qb_choices.id"]),
        CheckConstraint("(choice_id IS NOT NULL AND numeric_answer IS NULL) OR (choice_id IS NULL AND numeric_answer IS NOT NULL)"),
    )
    revision_id: Mapped[int] = mapped_column(ForeignKey("qb_revisions.id"), primary_key=True)
    choice_id: Mapped[int | None]
    # Future exact rational/decimal canonical value; no float tolerance policy yet.
    numeric_answer: Mapped[str | None] = mapped_column(String(100))


class Attempt(Base):
    __tablename__ = "qb_attempts"
    __table_args__ = (
        ForeignKeyConstraint(["question_id", "revision_id"], ["qb_revisions.question_id", "qb_revisions.id"]),
        ForeignKeyConstraint(["revision_id", "choice_id"], ["qb_choices.revision_id", "qb_choices.id"]),
        UniqueConstraint("student_id", "question_id", "number"),
        UniqueConstraint("student_id", "submission_key"),
        CheckConstraint("number > 0"), CheckConstraint("elapsed_ms IS NULL OR elapsed_ms >= 0"),
        CheckConstraint("(choice_id IS NOT NULL AND response_text IS NULL) OR (choice_id IS NULL AND response_text IS NOT NULL)"),
        Index("ix_qb_attempt_recent", "student_id", "created_at"),
        Index("ix_qb_attempt_question", "question_id", "created_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    question_id: Mapped[int]
    revision_id: Mapped[int]
    choice_id: Mapped[int | None]
    response_text: Mapped[str | None] = mapped_column(String(100))
    is_correct: Mapped[bool] = mapped_column(Boolean(create_constraint=True))
    number: Mapped[int]
    submission_key: Mapped[str] = mapped_column(String(64))
    elapsed_ms: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Bookmark(Base):
    __tablename__ = "qb_bookmarks"
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("qb_questions.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class PublicationEvent(Base):
    __tablename__ = 'qb_publication_events'
    __table_args__ = (
        ForeignKeyConstraint(['question_id', 'revision_id'], ['qb_revisions.question_id', 'qb_revisions.id']),
        CheckConstraint("action IN ('publish','unpublish','archive')"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey('qb_questions.id'), index=True)
    revision_id: Mapped[int]
    action: Mapped[str] = mapped_column(String(20))
    teacher_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
