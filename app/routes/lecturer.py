"""
Lecturer role — runs sessions, monitors live attendance, exports class sheet.
"""

from datetime import datetime, date, timedelta
from functools import wraps
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort,
    send_file, current_app, jsonify,
)
from io import BytesIO
from flask_login import login_required, current_user
import pandas as pd
from ..extensions import db
from ..models import (
    Lecturer, Course, ClassSession, AttendanceRecord, CourseRegistration, Student,
)

bp = Blueprint("lecturer", __name__, template_folder="../templates/lecturer")


def lecturer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "lecturer":
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _my_lecturer():
    return Lecturer.query.filter_by(user_id=current_user.id).first()


@bp.route("/")
@login_required
@lecturer_required
def dashboard():
    lec = _my_lecturer()
    if not lec:
        flash("Lecturer profile not found. Contact administrator.", "warning")
        return render_template("lecturer_dashboard.html", lec=None,
                               my_courses=[], today_sessions=[])
    my_courses = lec.courses
    today = date.today()
    today_sessions = (
        ClassSession.query.filter(
            ClassSession.course_id.in_([c.id for c in my_courses]),
            ClassSession.session_date == today,
        )
        .order_by(ClassSession.start_time)
        .all()
    )
    return render_template(
        "lecturer_dashboard.html",
        lec=lec,
        my_courses=my_courses,
        today_sessions=today_sessions,
    )


@bp.route("/session/<int:session_id>/live")
@login_required
@lecturer_required
def live_attendance(session_id):
    s = ClassSession.query.get_or_404(session_id)
    # Authorisation
    lec = _my_lecturer()
    if s.course.lecturer_id != lec.id:
        abort(403)
    return render_template("lecturer_live.html", session=s)


@bp.route("/session/<int:session_id>/data")
@login_required
@lecturer_required
def live_attendance_data(session_id):
    """JSON endpoint polled by the live page (auto-refresh)."""
    s = ClassSession.query.get_or_404(session_id)
    lec = _my_lecturer()
    if s.course.lecturer_id != lec.id:
        abort(403)
    regs = CourseRegistration.query.filter_by(course_id=s.course_id).all()
    students = sorted([r.student for r in regs], key=lambda x: x.full_name)
    rows = []
    for st in students:
        rec = AttendanceRecord.query.filter_by(session_id=s.id, student_id=st.id).first()
        rows.append({
            "index_number": st.index_number,
            "name": st.full_name,
            "status": rec.status if rec else "absent",
            "check_in": rec.check_in_time.strftime("%H:%M:%S") if rec and rec.check_in_time else None,
            "score": round(rec.similarity_score, 3) if rec and rec.similarity_score else None,
        })
    summary = {
        "present": sum(1 for r in rows if r["status"] == "present"),
        "late": sum(1 for r in rows if r["status"] == "late"),
        "absent": sum(1 for r in rows if r["status"] == "absent"),
        "total": len(rows),
    }
    return jsonify({"rows": rows, "summary": summary, "is_open": s.is_open})


@bp.route("/session/<int:session_id>/toggle", methods=["POST"])
@login_required
@lecturer_required
def toggle_session(session_id):
    s = ClassSession.query.get_or_404(session_id)
    lec = _my_lecturer()
    if s.course.lecturer_id != lec.id:
        abort(403)
    s.is_open = not s.is_open
    db.session.commit()
    flash(f"Session {'opened' if s.is_open else 'closed'} for attendance.", "info")
    return redirect(url_for("lecturer.live_attendance", session_id=s.id))


@bp.route("/session/<int:session_id>/export")
@login_required
@lecturer_required
def export_session(session_id):
    s = ClassSession.query.get_or_404(session_id)
    lec = _my_lecturer()
    if s.course.lecturer_id != lec.id:
        abort(403)
    regs = CourseRegistration.query.filter_by(course_id=s.course_id).all()
    rows = []
    for r in regs:
        rec = AttendanceRecord.query.filter_by(session_id=s.id, student_id=r.student.id).first()
        rows.append({
            "Index Number": r.student.index_number,
            "Full Name": r.student.full_name,
            "Status": (rec.status if rec else "absent").upper(),
            "Check-In Time": rec.check_in_time.strftime("%Y-%m-%d %H:%M:%S")
                             if rec and rec.check_in_time else "",
            "Similarity": round(rec.similarity_score, 3)
                          if rec and rec.similarity_score else "",
        })
    df = pd.DataFrame(rows)
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Attendance")
    out.seek(0)
    fname = f"{s.course.code.replace(' ', '_')}_{s.session_date}_attendance.xlsx"
    return send_file(out, as_attachment=True, download_name=fname,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@bp.route("/session/<int:session_id>/manual", methods=["POST"])
@login_required
@lecturer_required
def manual_override(session_id):
    s = ClassSession.query.get_or_404(session_id)
    lec = _my_lecturer()
    if s.course.lecturer_id != lec.id:
        abort(403)
    student_id = int(request.form["student_id"])
    new_status = request.form["status"]
    note = request.form.get("note", "")
    rec = AttendanceRecord.query.filter_by(session_id=s.id, student_id=student_id).first()
    if rec is None:
        rec = AttendanceRecord(session_id=s.id, student_id=student_id)
        db.session.add(rec)
    rec.status = new_status
    rec.source = "manual"
    rec.note = note
    rec.check_in_time = datetime.utcnow() if new_status in ("present", "late") else None
    db.session.commit()
    flash("Attendance manually updated.", "success")
    return redirect(url_for("lecturer.live_attendance", session_id=s.id))
