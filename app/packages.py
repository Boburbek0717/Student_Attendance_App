from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.database import write_transaction
from app.models import Attendance, BalanceAdjustment, Enrollment, LessonPackage, User


def package_rows(db: Session, enrollment_id: int):
    return db.execute(
        select(LessonPackage, func.count(Attendance.id))
        .outerjoin(Attendance, Attendance.package_id == LessonPackage.id)
        .where(LessonPackage.enrollment_id == enrollment_id)
        .group_by(LessonPackage.id).order_by(LessonPackage.purchased_at, LessonPackage.id)
    ).all()


def package_balance(rows, adjustments=()):
    """Calculate credit from recorded packages and attendance, never a stored counter."""
    included = sum(package.lesson_limit for package, used in rows)
    attended = sum(used for package, used in rows)
    adjustment = sum(item.delta for item in adjustments)
    net = included + adjustment - attended
    packages = []
    carried = 0
    for package, used in rows:
        carried_in = carried
        remaining = package.lesson_limit - used - carried
        carried = max(0, -remaining)
        packages.append({
            "id": package.id, "limit": package.lesson_limit, "used": used,
            "remaining": max(0, remaining), "carried_in": carried_in,
            "carried_out": carried, "purchased_at": package.purchased_at,
        })
    # Reconcile package credit with the corrected total. Corrections can cause
    # later attendance to use a different package than the original purchase order.
    difference = max(0, net) - sum(item['remaining'] for item in packages)
    if packages and difference > 0:
        packages[-1]['remaining'] += difference
    elif difference < 0:
        deduction = -difference
        for item in packages:
            removed = min(deduction, item['remaining'])
            item['remaining'] -= removed
            deduction -= removed
    available_packages = [item for item in packages if item["remaining"] > 0]
    queued = sum(item["remaining"] for item in available_packages[1:])
    return {
        "included": included, "attended": attended, "balance": net,
        "adjustment": adjustment,
        "latest_adjustment_id": max((item.id for item in adjustments), default=0),
        "available": max(0, net), "owed": max(0, -net),
        "latest_package_id": max((package.id for package, used in rows), default=0),
        "packages": packages,
        "queued": queued,
    }


def renew_package(engine: Engine, teacher_id: int, enrollment_id: int,
                  expected_package_id: int, expected_attended: int, expected_adjustment_id: int = 0) -> int:
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
        balance = enrollment_balance(db, enrollment.id)
        if (balance["latest_package_id"], balance["attended"], balance["latest_adjustment_id"]) != (expected_package_id, expected_attended, expected_adjustment_id):
            raise ValueError("The balance changed or this renewal was already recorded. Review the updated balance before confirming again.")
        package = LessonPackage(enrollment_id=enrollment.id, lesson_limit=12)
        db.add(package)
        db.flush()
        return package.id


def adjustment_rows(db, enrollment_id):
    return db.scalars(select(BalanceAdjustment).where(
        BalanceAdjustment.enrollment_id == enrollment_id,
    ).order_by(BalanceAdjustment.id)).all()


def enrollment_balance(db, enrollment_id):
    return package_balance(package_rows(db, enrollment_id), adjustment_rows(db, enrollment_id))


def balance_version(balance):
    return f"{balance['latest_package_id']}:{balance['attended']}:{balance['latest_adjustment_id']}"


def set_balance(engine, teacher_id, student_id, enrollment_id, target, reason, expected_version):
    if not -1000000 <= target <= 1000000:
        raise ValueError("Enter a whole-number balance between -1000000 and 1000000.")
    reason = reason.strip()
    if not 1 <= len(reason) <= 500:
        raise ValueError("Enter a reason of 1–500 characters for this correction.")
    with write_transaction(engine) as db:
        teacher = db.get(User, teacher_id)
        if teacher is None or teacher.role != 'teacher':
            raise ValueError("Only a teacher can adjust balances.")
        enrollment = db.get(Enrollment, enrollment_id) if 0 < enrollment_id < 2**63 else None
        if enrollment is None or enrollment.student_id != student_id:
            raise ValueError("Enrollment not found for this student.")
        student = db.get(User, enrollment.student_id)
        if student is None or student.role != 'student':
            raise ValueError("Choose a student enrollment.")
        balance = enrollment_balance(db, enrollment.id)
        if not balance['packages']:
            raise ValueError("This enrollment needs an initial lesson package first.")
        if expected_version != balance_version(balance):
            raise ValueError("The balance changed. Review the updated balance before saving again.")
        if target == balance['balance']:
            return
        db.add(BalanceAdjustment(enrollment_id=enrollment.id, teacher_id=teacher_id,
                                 old_balance=balance['balance'], new_balance=target,
                                 delta=target - balance['balance'], reason=reason))
