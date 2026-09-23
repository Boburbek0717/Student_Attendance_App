from datetime import timedelta
import re
import secrets

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session
from fastapi import Request, HTTPException

from app.models import Attendance, Enrollment, Group, Lesson, LessonPackage, LessonRoster, LessonRosterSnapshot, BalanceAdjustment, User, utc_now
from app.database import write_transaction
from app.packages import package_balance, enrollment_balance
from app.security import current_user


def new_attendance_code(db: Session, now, previous_code=None) -> str:
    for _ in range(100):
        code = f"{secrets.randbelow(1_000_000):06d}"
        if code == previous_code:
            continue
        collision = db.scalar(select(Lesson.id).where(
            Lesson.attendance_code == code, Lesson.code_expires_at > now,
        ))
        if collision is None:
            return code
    raise ValueError("Could not create a unique code. Please try again.")


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
        code = new_attendance_code(db, now)
        lesson = Lesson(group_id=group_id, started_at=now, attendance_code=code,
                        code_expires_at=now + timedelta(minutes=minutes))
        db.add(lesson)
        db.flush()
        db.add(LessonRosterSnapshot(lesson_id=lesson.id, captured_at=now))
        db.flush()
        enrollment_ids = db.scalars(select(Enrollment.id).where(
            Enrollment.group_id == group_id, Enrollment.active.is_(True),
        )).all()
        db.add_all([LessonRoster(lesson_id=lesson.id, enrollment_id=key) for key in enrollment_ids])
        return lesson.id


def check_in(engine: Engine, student_id: int, code: str, *, request: Request | None = None) -> int:
    code = code.strip()
    if not re.fullmatch(r"[0-9]{6}", code):
        raise ValueError("Enter the six-digit code from your teacher.")
    with write_transaction(engine) as db:
        if request is not None:
            actor = current_user(request, db)
            if actor is None or actor.id != student_id:
                raise HTTPException(303, headers={"Location": "/login"})
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
            raise ValueError("That code is invalid or has expired. Ask your teacher for the current code.")
        duplicate = db.scalar(select(Attendance.id).where(
            Attendance.enrollment_id == enrollment.id, Attendance.lesson_id == lesson.id,
        ))
        if duplicate is not None:
            raise ValueError("You have already checked in to this lesson. No extra lesson was used.")
        balance = enrollment_balance(db, enrollment.id)
        if not balance["packages"]:
            raise ValueError("You have no lesson package in this group. Please contact your teacher.")
        # Once paid credit is exhausted, keep attendance on the latest package.
        # Its excess carries into later renewals; historical rows never move.
        package = next((item for item in balance["packages"] if item["remaining"] > 0),
                       balance["packages"][-1])
        db.add(Attendance(enrollment_id=enrollment.id, lesson_id=lesson.id,
                          package_id=package["id"], checked_in_at=now))
        return balance["balance"] - 1


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
    rows_by_enrollment = {}
    for package, used in packages:
        rows_by_enrollment.setdefault(package.enrollment_id, []).append((package, used))
    adjustments = db.scalars(select(BalanceAdjustment).join(
        Enrollment, Enrollment.id == BalanceAdjustment.enrollment_id,
    ).where(Enrollment.student_id == student_id).order_by(BalanceAdjustment.id)).all()
    adjustments_by_enrollment = {}
    for adjustment in adjustments:
        adjustments_by_enrollment.setdefault(adjustment.enrollment_id, []).append(adjustment)
    balances = {enrollment.id: package_balance(rows_by_enrollment.get(enrollment.id, []),
                adjustments_by_enrollment.get(enrollment.id, []))
                for enrollment, group in memberships}
    by_enrollment = {key: balance["packages"] for key, balance in balances.items()}
    history = db.execute(
        select(Attendance.checked_in_at, Attendance.package_id, Lesson.id.label("lesson_id"),
               Lesson.started_at, Group.name.label("group_name"))
        .join(Lesson, Lesson.id == Attendance.lesson_id)
        .join(Group, Group.id == Lesson.group_id)
        .join(Enrollment, Enrollment.id == Attendance.enrollment_id)
        .where(Enrollment.student_id == student_id)
        .order_by(Attendance.checked_in_at.desc(), Attendance.id.desc())
    ).all()
    return {"memberships": memberships, "packages_by_enrollment": by_enrollment,
            "balances": balances, "history": history, "adjustments_by_enrollment": adjustments_by_enrollment}
