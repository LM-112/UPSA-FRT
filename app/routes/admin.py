"""
Admin role routes — for Department / School Administrators.
Capabilities:
    - View dashboard with attendance KPIs
    - Manage students, lecturers, courses
    - Trigger face enrolment to the terminal
    - Generate attendance reports (CSV/Excel)
    - Send absenteeism alerts
"""

from io import BytesIO
from datetime import datetime, date, timedelta
from functools import wraps
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
    send_file, current_app, abort,
)
from flask_login import login_required, current_user
from sqlalchemy import func
import pandas as pd
from ..extensions import db
from ..models import (
    Student, Lecturer, Course, ClassSession, AttendanceRecord,
    Programme, Department, Faculty, HikDevice, EnrollmentLog,
    CourseRegistration, User,
)
from ..services.hikvision_client import HikvisionTerminal

bp = Blueprint("admin", __name__, template_folder="../templates/admin")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ("admin", "super"):
            abort(403)
        return f(*args, **kwargs)
    return decorated


@bp.route("/")
@login_required
@admin_required
def dashboard():
    today = date.today()
    total_students = Student.query.count()
    total_lecturers = Lecturer.query.count()
    total_courses = Course.query.count()
    enrolled_on_terminal = Student.query.filter_by(enrolled_on_terminal=True).count()

    # Today KPIs
    today_sessions = ClassSession.query.filter_by(session_date=today).all()
    session_ids = [s.id for s in today_sessions]
    today_records = (
        AttendanceRecord.query.filter(AttendanceRecord.session_id.in_(session_ids)).all()
        if session_ids else []
    )
    today_present = sum(1 for r in today_records if r.status == "present")
    today_late = sum(1 for r in today_records if r.status == "late")

    # 7-day attendance trend
    seven_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    trend = []
    for d in seven_days:
        sids = [s.id for s in ClassSession.query.filter_by(session_date=d).all()]
        if sids:
            present = AttendanceRecord.query.filter(
                AttendanceRecord.session_id.in_(sids),
                AttendanceRecord.status.in_(["present", "late"]),
            ).count()
            total = AttendanceRecord.query.filter(
                AttendanceRecord.session_id.in_(sids)
            ).count()
            rate = round(100 * present / total, 1) if total else 0
        else:
            rate = 0
        trend.append({"date": d.strftime("%a %d"), "rate": rate})

    return render_template(
        "admin_dashboard.html",
        total_students=total_students,
        total_lecturers=total_lecturers,
        total_courses=total_courses,
        enrolled_on_terminal=enrolled_on_terminal,
        today_present=today_present,
        today_late=today_late,
        today_sessions=len(today_sessions),
        trend=trend,
    )


# ----- Students --------------------------------------------------------------
@bp.route("/students")
@login_required
@admin_required
def students_list():
    q = request.args.get("q", "").strip()
    query = Student.query
    if q:
        query = query.filter(
            db.or_(
                Student.full_name.ilike(f"%{q}%"),
                Student.index_number.ilike(f"%{q}%"),
                Student.employee_id.ilike(f"%{q}%"),
            )
        )
    students = query.order_by(Student.full_name).limit(200).all()
    return render_template("admin_students.html", students=students, q=q)


@bp.route("/students/<int:student_id>/enroll-on-terminal", methods=["POST"])
@login_required
@admin_required
def enroll_student_on_terminal(student_id):
    student = Student.query.get_or_404(student_id)
    devices = HikDevice.query.filter_by(is_active=True).all()
    if not devices:
        flash("No active terminal registered.", "danger")
        return redirect(url_for("admin.students_list"))

    if not student.consent_given:
        flash("Consent has not been recorded for this student. Cannot enroll.", "warning")
        return redirect(url_for("admin.students_list"))

    image_bytes = b""
    if student.photo_path:
        photo_full = current_app.config["UPLOAD_FOLDER"] / student.photo_path
        if photo_full.exists():
            image_bytes = photo_full.read_bytes()

    successes = 0
    for d in devices:
        term = HikvisionTerminal(
            host=d.ip_address, port=d.port,
            username=d.username, password=d.password,
            simulate=current_app.config.get("HIKVISION_SIMULATE", False),
        )
        ok, msg = term.add_person(employee_id=student.employee_id, name=student.full_name,
                                  gender=student.gender or "male")
        db.session.add(EnrollmentLog(student_id=student.id, device_id=d.id,
                                     action="add_person", success=ok, response_text=msg))
        if ok and image_bytes:
            ok2, msg2 = term.add_face_picture(student.employee_id, image_bytes)
            db.session.add(EnrollmentLog(student_id=student.id, device_id=d.id,
                                         action="add_face", success=ok2, response_text=msg2))
            ok = ok and ok2
        if ok:
            successes += 1

    student.enrolled_on_terminal = successes > 0
    db.session.commit()
    if successes:
        flash(f"Student enrolled on {successes} device(s).", "success")
    else:
        flash("Enrolment failed. See enrolment logs for detail.", "danger")
    return redirect(url_for("admin.students_list"))


# ----- Reports ---------------------------------------------------------------
@bp.route("/reports")
@login_required
@admin_required
def reports():
    courses = Course.query.order_by(Course.code).all()
    return render_template("admin_reports.html", courses=courses)


@bp.route("/reports/course/<int:course_id>/export")
@login_required
@admin_required
def export_course_report(course_id):
    course = Course.query.get_or_404(course_id)
    sessions = (
        ClassSession.query.filter_by(course_id=course.id)
        .order_by(ClassSession.session_date, ClassSession.start_time)
        .all()
    )

    # Build a wide DataFrame: rows = students, columns = sessions
    regs = CourseRegistration.query.filter_by(course_id=course.id).all()
    students = [r.student for r in regs]
    rows = []
    for s in students:
        row = {"Index Number": s.index_number, "Full Name": s.full_name}
        present_count = late_count = absent_count = 0
        for sess in sessions:
            rec = AttendanceRecord.query.filter_by(
                session_id=sess.id, student_id=s.id
            ).first()
            label = (rec.status if rec else "absent").upper()[:1]
            if label == "P":
                present_count += 1
            elif label == "L":
                late_count += 1
            else:
                absent_count += 1
            row[f"{sess.session_date} {sess.start_time}"] = label
        total = max(1, len(sessions))
        row["Present%"] = round(100 * present_count / total, 1)
        row["Late%"] = round(100 * late_count / total, 1)
        row["Absent%"] = round(100 * absent_count / total, 1)
        rows.append(row)

    df = pd.DataFrame(rows)
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=course.code.replace(" ", "_")[:30])
    out.seek(0)
    fname = f"UPSA_{course.code.replace(' ', '_')}_attendance.xlsx"
    return send_file(out, as_attachment=True, download_name=fname,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ----- Courses ---------------------------------------------------------------
@bp.route("/courses")
@login_required
@admin_required
def courses_list():
    courses = Course.query.order_by(Course.code).all()
    return render_template("admin_courses.html", courses=courses)


# ----- Devices ---------------------------------------------------------------
@bp.route("/devices")
@login_required
@admin_required
def devices_list():
    devices = HikDevice.query.all()
    statuses = []
    for d in devices:
        term = HikvisionTerminal(
            host=d.ip_address, port=d.port,
            username=d.username, password=d.password,
            simulate=current_app.config.get("HIKVISION_SIMULATE", False),
        )
        info = term.get_device_info()
        statuses.append({"device": d, "info": info, "online": info is not None})
    return render_template("admin_devices.html", statuses=statuses)
