"""
Student role — view personal attendance, justify absences, see schedule.
"""

from datetime import date
from functools import wraps
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort,
)
from flask_login import login_required, current_user
from ..extensions import db
from ..models import (
    Student, Course, ClassSession, AttendanceRecord, CourseRegistration,
)

bp = Blueprint("student", __name__, template_folder="../templates/student")


def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "student":
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _me():
    return Student.query.filter_by(user_id=current_user.id).first()


@bp.route("/")
@login_required
@student_required
def dashboard():
    me = _me()
    if not me:
        flash("Student profile not linked. Contact administrator.", "warning")
        return render_template("student_dashboard.html", me=None,
                               summary={}, courses=[])

    regs = CourseRegistration.query.filter_by(student_id=me.id).all()
    courses_data = []
    overall = {"present": 0, "late": 0, "absent": 0, "total": 0}
    for r in regs:
        sessions = ClassSession.query.filter_by(course_id=r.course_id).all()
        present = late = absent = 0
        for s in sessions:
            rec = AttendanceRecord.query.filter_by(
                session_id=s.id, student_id=me.id
            ).first()
            status = rec.status if rec else "absent"
            if status == "present":
                present += 1
            elif status == "late":
                late += 1
            else:
                absent += 1
        total = len(sessions) or 1
        rate = round(100 * (present + late) / total, 1)
        courses_data.append({
            "course": r.course,
            "present": present,
            "late": late,
            "absent": absent,
            "total": len(sessions),
            "rate": rate,
        })
        overall["present"] += present
        overall["late"] += late
        overall["absent"] += absent
        overall["total"] += len(sessions)

    rate = (
        round(100 * (overall["present"] + overall["late"]) / overall["total"], 1)
        if overall["total"] else 0
    )
    overall["rate"] = rate
    return render_template("student_dashboard.html", me=me, courses=courses_data,
                           summary=overall)


@bp.route("/course/<int:course_id>")
@login_required
@student_required
def course_detail(course_id):
    me = _me()
    course = Course.query.get_or_404(course_id)
    # Verify registration
    reg = CourseRegistration.query.filter_by(student_id=me.id, course_id=course.id).first()
    if not reg:
        abort(403)
    sessions = (
        ClassSession.query.filter_by(course_id=course.id)
        .order_by(ClassSession.session_date.desc())
        .all()
    )
    rows = []
    for s in sessions:
        rec = AttendanceRecord.query.filter_by(session_id=s.id, student_id=me.id).first()
        rows.append({"session": s, "record": rec})
    return render_template("student_course.html", course=course, rows=rows)
