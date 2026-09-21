from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.database import write_transaction
from app.models import Attendance, Enrollment, LessonPackage, User


def package_rows(db: Session, enrollment_id: int):
    return db.execute(
        select(LessonPackage, func.count(Attendance.id))
        .outerjoin(Attendance, Attendance.package_id == LessonPackage.id)
        .where(LessonPackage.enrollment_id == enrollment_id)
        .group_by(LessonPackage.id).order_by(LessonPackage.purchased_at, LessonPackage.id)
    ).all()


def package_balance(rows):
    """Calculate credit from recorded packages and attendance, never a stored counter."""
    included = sum(package.lesson_limit for package, used in rows)
    attended = sum(used for package, used in rows)
    packages = []
    carried = 0
    for package, used in rows:
        carried_in = carried
        remaining = package.lesson_limit - used - carried_in
        carried = max(0, -remaining)
        packages.append({
            "id": package.id, "limit": package.lesson_limit, "used": used,
            "remaining": max(0, remaining), "carried_in": carried_in,
            "carried_out": carried, "purchased_at": package.purchased_at,
        })
    available_packages = [item for item in packages if item["remaining"] > 0]
    queued = sum(item["remaining"] for item in available_packages[1:])
    return {
        "included": included, "attended": attended, "balance": included - attended,
        "available": max(0, included - attended), "owed": max(0, attended - included),
        "latest_package_id": max((package.id for package, used in rows), default=0),
        "packages": packages,
        "queued": queued,
    }


def renew_package(engine: Engine, teacher_id: int, enrollment_id: int,
                  expected_package_id: int, expected_attended: int) -> int:
    if not 0 < enrollment_id < 2**63:
        raise ValueError("Enrollment not found.")
    with write_transaction(engine) as db:
        teacher = db.get(User, teacher_id)
        if teacher is None or teacher.role != "teacher":
            raise ValueError("Only a teacher can renew a package.")
        enrollment = db.get(Enrollment, enrollment_id)
        if enrollment is None or not enrollment.active:
            raise ValueError("Choose an active enrollment to renew.")
        student = db.get(User, enrollment.student_id)
        if student is None or student.role != "student":
            raise ValueError("This enrollment does not belong to a student.")
        balance = package_balance(package_rows(db, enrollment.id))
        if (balance["latest_package_id"], balance["attended"]) != (expected_package_id, expected_attended):
            raise ValueError("The balance changed or this renewal was already recorded. Review the updated balance before confirming again.")
        package = LessonPackage(enrollment_id=enrollment.id, lesson_limit=12)
        db.add(package)
        db.flush()
        return package.id
