from datetime import datetime, timezone

from sqlalchemy import JSON, Float, Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    # SQLite stores naive datetimes; all timestamps in this app represent UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('teacher', 'student')", name="valid_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="student")


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


class LoginSession(Base):
    __tablename__ = "login_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    credential_fingerprint: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("student_id", "group_id", name="one_membership"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    active: Mapped[bool] = mapped_column(Boolean(create_constraint=True), default=True)


class LessonPackage(Base):
    __tablename__ = "lesson_packages"
    __table_args__ = (
        CheckConstraint("lesson_limit > 0", name="positive_lesson_limit"),
        UniqueConstraint("id", "enrollment_id", name="package_owner"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id"))
    lesson_limit: Mapped[int] = mapped_column(default=12)
    purchased_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        CheckConstraint(
            "(attendance_code IS NULL AND code_expires_at IS NULL) OR "
            "(attendance_code IS NOT NULL AND code_expires_at IS NOT NULL "
            "AND code_expires_at > started_at)",
            name="valid_code_window",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    attendance_code: Mapped[str | None] = mapped_column(String(6))
    code_expires_at: Mapped[datetime | None] = mapped_column(DateTime)


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("enrollment_id", "lesson_id", name="one_check_in"),
        ForeignKeyConstraint(
            ["package_id", "enrollment_id"],
            ["lesson_packages.id", "lesson_packages.enrollment_id"],
            name="attendance_package_owner",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"))
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id"))
    package_id: Mapped[int]
    checked_in_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class BalanceAdjustment(Base):
    __tablename__ = "balance_adjustments"
    __table_args__ = (CheckConstraint("new_balance - old_balance = delta", name="consistent_adjustment"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    old_balance: Mapped[int]
    new_balance: Mapped[int]
    delta: Mapped[int]
    reason: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class LessonRosterSnapshot(Base):
    __tablename__ = "lesson_roster_snapshots"

    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), primary_key=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class LessonRoster(Base):
    __tablename__ = "lesson_roster"

    lesson_id: Mapped[int] = mapped_column(ForeignKey("lesson_roster_snapshots.lesson_id"), primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id"), primary_key=True)


class AttendanceAttemptWindow(Base):
    __tablename__ = "attendance_attempt_windows"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    timestamps: Mapped[list[float]] = mapped_column(JSON)


class LoginAttemptWindow(Base):
    __tablename__ = "login_attempt_windows"
    key: Mapped[str] = mapped_column(String(66), primary_key=True)
    timestamps: Mapped[list[float]] = mapped_column(JSON)
    updated_at: Mapped[float] = mapped_column(Float, index=True)


class AttendanceCorrection(Base):
    __tablename__ = "attendance_corrections"
    __table_args__ = (CheckConstraint("action IN ('manual', 'reverse', 'restore')", name="valid_attendance_action"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    attendance_id: Mapped[int] = mapped_column(ForeignKey("attendance.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
