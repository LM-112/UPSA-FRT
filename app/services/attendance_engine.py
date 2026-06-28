"""
Attendance engine — turns raw recognition events into AttendanceRecord rows.

When the Hikvision DS-K1T342MFX-E1 recognises a student's face, it pushes us
an event with three things we care about:
    - employeeNoString (== UPSA index number)
    - similarity score (0..1)
    - timestamp

This engine answers: "Given that recognition, which class session does it
belong to, and should the student be marked present, late, or rejected?"

Decision tree:
    1. Find any ClassSession that:
         - is_open OR within attendance window
         - contains a Course in which this student is registered
       If none → log event but mark unmatched.
    2. If session.start - now < ATTENDANCE_OPEN_BEFORE_MIN -> 'present'
       (i.e. early or on time)
    3. If now <= session.start + ATTENDANCE_PRESENT_GRACE_MIN -> 'present'
    4. If now <= session.end_time -> 'late'
    5. Else -> reject (session over).
    6. Reject if similarity < MIN_RECOGNITION_SIMILARITY.
"""

from datetime import datetime, timedelta, date as date_type
from typing import Optional
from flask import current_app
from ..extensions import db
from ..models import (
    Student,
    Course,
    ClassSession,
    CourseRegistration,
    AttendanceRecord,
    EventLog,
)


def _now() -> datetime:
    return datetime.utcnow()


def find_active_session_for_student(
    student: Student, when: datetime
) -> Optional[ClassSession]:
    """
    Return the most relevant ClassSession for this student at this moment.
    Strategy: among the courses the student is registered in, pick a session
    on today's date whose attendance window contains `when`.
    """
    today: date_type = when.date()
    course_ids = [r.course_id for r in student.course_registrations]
    if not course_ids:
        return None

    open_before = current_app.config["ATTENDANCE_OPEN_BEFORE_MIN"]

    candidates = (
        ClassSession.query.filter(
            ClassSession.course_id.in_(course_ids),
            ClassSession.session_date == today,
        )
        .order_by(ClassSession.start_time)
        .all()
    )
    for cs in candidates:
        start_dt = datetime.combine(cs.session_date, cs.start_time)
        end_dt = datetime.combine(cs.session_date, cs.end_time)
        window_open = start_dt - timedelta(minutes=open_before)
        if window_open <= when <= end_dt:
            return cs
    return None


def classify_attendance(
    when: datetime, session: ClassSession
) -> str:
    grace = current_app.config["ATTENDANCE_PRESENT_GRACE_MIN"]
    start_dt = datetime.combine(session.session_date, session.start_time)
    end_dt = datetime.combine(session.session_date, session.end_time)
    if when <= start_dt + timedelta(minutes=grace):
        return "present"
    if when <= end_dt:
        return "late"
    return "absent"


def process_recognition_event(
    employee_id: str,
    similarity: float,
    occurred_at: datetime,
    device_id: int | None = None,
    raw_payload: str | None = None,
) -> dict:
    """
    Main entry-point. Idempotent: if an AttendanceRecord already exists for
    (session, student) we update it only if we have a 'better' status
    (present beats late beats absent).
    """
    result = {
        "ok": False,
        "reason": None,
        "student_id": None,
        "session_id": None,
        "status": None,
    }

    student = Student.query.filter_by(employee_id=employee_id).first()
    elog = EventLog(
        device_id=device_id,
        employee_id_seen=employee_id,
        similarity=similarity,
        occurred_at=occurred_at,
        raw_payload=raw_payload,
    )
    db.session.add(elog)

    if not student:
        result["reason"] = "unknown_employee_id"
        db.session.commit()
        return result

    min_sim = current_app.config["MIN_RECOGNITION_SIMILARITY"]
    if similarity is not None and similarity < min_sim:
        result["reason"] = "low_similarity"
        db.session.commit()
        return result

    session = find_active_session_for_student(student, occurred_at)
    if not session:
        result["reason"] = "no_active_session"
        db.session.commit()
        return result

    elog.matched_session_id = session.id
    status = classify_attendance(occurred_at, session)
    if status == "absent":
        result["reason"] = "session_already_ended"
        db.session.commit()
        return result

    record = AttendanceRecord.query.filter_by(
        session_id=session.id, student_id=student.id
    ).first()
    if record is None:
        record = AttendanceRecord(
            session_id=session.id,
            student_id=student.id,
            status=status,
            check_in_time=occurred_at,
            similarity_score=similarity,
            source="terminal",
        )
        db.session.add(record)
    else:
        # Upgrade: present > late > absent. Never downgrade.
        rank = {"present": 3, "late": 2, "absent": 1, "excused": 0}
        if rank.get(status, 0) > rank.get(record.status, 0):
            record.status = status
            record.check_in_time = occurred_at
            record.similarity_score = similarity

    elog.processed = True
    db.session.commit()

    result.update(
        ok=True,
        reason="recorded",
        student_id=student.id,
        session_id=session.id,
        status=status,
    )
    return result
