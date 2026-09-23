"""Read effective attendance without deleting original records or audit events."""
from sqlalchemy import func, select
from app.models import Attendance, AttendanceCorrection


def latest_action():
    return select(AttendanceCorrection.action).where(
        AttendanceCorrection.attendance_id == Attendance.id,
    ).order_by(AttendanceCorrection.id.desc()).limit(1).correlate(Attendance).scalar_subquery()


def attendance_active():
    return func.coalesce(latest_action(), 'code') != 'reverse'


def attendance_origin():
    first = select(AttendanceCorrection.action).where(
        AttendanceCorrection.attendance_id == Attendance.id,
    ).order_by(AttendanceCorrection.id).limit(1).correlate(Attendance).scalar_subquery()
    return func.coalesce(first, 'code') == 'manual'


def correction_version(db, enrollment_id):
    return db.scalar(select(func.max(AttendanceCorrection.id)).join(
        Attendance, Attendance.id == AttendanceCorrection.attendance_id,
    ).where(Attendance.enrollment_id == enrollment_id)) or 0
