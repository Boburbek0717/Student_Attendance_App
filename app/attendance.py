from contextlib import contextmanager
from datetime import timedelta
import re
import secrets

from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models import Attendance, Enrollment, Group, Lesson, LessonPackage, User, utc_now


@contextmanager
def write_transaction(engine: Engine):
    """Serialize validation and writes so concurrent requests see fresh balances."""
    with Session(engine) as db:
        try:
            db.execute(text("BEGIN IMMEDIATE"))
            yield db
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise ValueError("The record could not be saved. Refresh and check your history before retrying.") from error
        except OperationalError as error:
            db.rollback()
            if (getattr(error.orig, "sqlite_errorcode", 0) & 255) in (5, 6):
                raise ValueError("The database is busy. Please try again in a moment.") from error
            raise


def start_lesson(engine: Engine, teacher_id: int, group_id: int, minutes: int = 15) -> int:
    if not 0 < group_id < 2**63 or not 1 <= minutes <= 60:
        raise ValueError("Choose a valid group and a code duration of 1–60 minutes.")
    with write_transaction(engine) as db:
        teacher = db.get(User, teacher_id)
        if teacher is None or teacher.role != "teacher":
            raise ValueError("Only a teacher can start a lesson.")
        if db.get(Group, group_id) is None:
            raise ValueError("This group no longer exists.")
        now = utc_now()
        existing = db.scalar(select(Lesson).where(
            Lesson.group_id == group_id, Lesson.started_at <= now, Lesson.code_expires_at > now,
        ).order_by(Lesson.id.desc()))
        if existing is not None:
            return existing.id
        for _ in range(100):
            code = f"{secrets.randbelow(1_000_000):06d}"
            collision = db.scalar(select(Lesson.id).where(
                Lesson.attendance_code == code, Lesson.code_expires_at > now,
            ))
            if collision is None:
                break
        else:
            raise ValueError("Could not create a unique code. Please try again.")
        lesson = Lesson(group_id=group_id, started_at=now, attendance_code=code,
                        code_expires_at=now + timedelta(minutes=minutes))
        db.add(lesson)
        db.flush()
        return lesson.id


def check_in(engine: Engine, student_id: int, code: str) -> None:
    code = code.strip()
    if not re.fullmatch(r"[0-9]{6}", code):
        raise ValueError("Enter the six-digit code from your teacher.")
    with write_transaction(engine) as db:
        student = db.get(User, student_id)
        if student is None or student.role != "student":
            raise ValueError("Only a student can check in.")
        now = utc_now()
        lessons = db.scalars(select(Lesson).where(
            Lesson.attendance_code == code, Lesson.started_at <= now, Lesson.code_expires_at > now,
        )).all()
        if len(lessons) != 1:
            raise ValueError("That code is invalid or has expired. Ask your teacher for the current code.")
        lesson = lessons[0]
        enrollment = db.scalar(select(Enrollment).where(
            Enrollment.student_id == student_id, Enrollment.group_id == lesson.group_id,
            Enrollment.active.is_(True),
        ))
        if enrollment is None:
            raise ValueError("You do not have an active enrollment in this lesson's group.")
        duplicate = db.scalar(select(Attendance.id).where(
            Attendance.enrollment_id == enrollment.id, Attendance.lesson_id == lesson.id,
        ))
        if duplicate is not None:
            raise ValueError("You have already checked in to this lesson. No extra lesson was used.")
        used = select(func.count(Attendance.id)).where(
            Attendance.package_id == LessonPackage.id,
        ).correlate(LessonPackage).scalar_subquery()
        package = db.scalar(select(LessonPackage).where(
            LessonPackage.enrollment_id == enrollment.id, used < LessonPackage.lesson_limit,
        ).order_by(LessonPackage.purchased_at, LessonPackage.id))
        if package is None:
            raise ValueError("You have no lessons remaining in this group. Please contact your teacher.")
        db.add(Attendance(enrollment_id=enrollment.id, lesson_id=lesson.id,
                          package_id=package.id, checked_in_at=now))


def student_records(db: Session, student_id: int):
    memberships = db.execute(select(Enrollment, Group).join(Group).where(
        Enrollment.student_id == student_id,
    ).order_by(Group.name, Enrollment.id)).all()
    packages = db.execute(
        select(LessonPackage, func.count(Attendance.id))
        .join(Enrollment, Enrollment.id == LessonPackage.enrollment_id)
        .outerjoin(Attendance, Attendance.package_id == LessonPackage.id)
        .where(Enrollment.student_id == student_id)
        .group_by(LessonPackage.id).order_by(LessonPackage.purchased_at, LessonPackage.id)
    ).all()
    by_enrollment = {}
    for package, used in packages:
        by_enrollment.setdefault(package.enrollment_id, []).append({
            "id": package.id, "limit": package.lesson_limit, "used": used,
            "remaining": package.lesson_limit - used,
        })
    history = db.execute(
        select(Attendance.checked_in_at, Attendance.package_id, Lesson.id.label("lesson_id"),
               Lesson.started_at, Group.name.label("group_name"))
        .join(Lesson, Lesson.id == Attendance.lesson_id)
        .join(Group, Group.id == Lesson.group_id)
        .join(Enrollment, Enrollment.id == Attendance.enrollment_id)
        .where(Enrollment.student_id == student_id)
        .order_by(Attendance.checked_in_at.desc(), Attendance.id.desc())
    ).all()
    return {"memberships": memberships, "packages_by_enrollment": by_enrollment, "history": history}
