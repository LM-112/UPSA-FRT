"""
Database models for the UPSA FRT Attendance System.

Schema map (matches Chapter 4 of the thesis exactly):
    User              -- system login (lecturer / admin / student / super)
    Faculty/School    -- UPSA's faculties (e.g. Faculty of IT & Communication)
    Department        -- e.g. Department of Information Technology Studies
    Programme         -- e.g. BSc Information Technology Management
    Student           -- enrolled student profile
    Lecturer          -- teaching staff profile
    Course            -- offered course (CSCD 415, MGMT 305, etc.)
    CourseRegistration-- which student is taking which course this semester
    ClassSession      -- a single scheduled lecture/lab (date+time+venue)
    AttendanceRecord  -- one row per (student, session): present/late/absent
    HikDevice         -- registered Hikvision terminal (we may have several rooms)
    EnrollmentLog     -- audit of face enrolments pushed to the terminal(s)
    EventLog          -- raw recognition events received from the terminal
"""

from datetime import datetime, date, time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from .extensions import db


# ---------------------------------------------------------------------------
# Identity & access
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(
        db.String(20), nullable=False
    )  # 'super', 'admin', 'lecturer', 'student'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime)

    # Optional links (a User row may belong to a Student or Lecturer profile)
    student = db.relationship("Student", backref="user", uselist=False)
    lecturer = db.relationship("Lecturer", backref="user", uselist=False)

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    @property
    def is_admin(self):
        return self.role in ("admin", "super")

    @property
    def is_super(self):
        return self.role == "super"


# ---------------------------------------------------------------------------
# UPSA org structure
# ---------------------------------------------------------------------------
class Faculty(db.Model):
    __tablename__ = "faculties"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    departments = db.relationship("Department", backref="faculty", lazy=True)


class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculties.id"), nullable=False)
    programmes = db.relationship("Programme", backref="department", lazy=True)


class Programme(db.Model):
    __tablename__ = "programmes"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    department_id = db.Column(
        db.Integer, db.ForeignKey("departments.id"), nullable=False
    )
    students = db.relationship("Student", backref="programme", lazy=True)


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------
class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)

    # 'employee_id' is what the Hikvision terminal calls the unique identifier.
    # For UPSA we use the student ID number printed on the card (e.g., '10300137').
    employee_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    index_number = db.Column(db.String(32), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    gender = db.Column(db.String(10))
    nationality = db.Column(db.String(40), default="Ghanaian")
    date_of_birth = db.Column(db.Date)
    level = db.Column(db.Integer)  # current level: 100, 200, 300, 400
    entry_level = db.Column(db.Integer)  # level the student entered at
    hall = db.Column(db.String(60))  # UPSA hall, e.g. "Yaa Asantewaa", "Africa"
    programme_id = db.Column(db.Integer, db.ForeignKey("programmes.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    photo_path = db.Column(db.String(255))  # path inside static/uploads/
    enrolled_on_terminal = db.Column(db.Boolean, default=False)
    consent_given = db.Column(db.Boolean, default=False)
    consent_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    course_registrations = db.relationship(
        "CourseRegistration", backref="student", lazy=True
    )
    attendance_records = db.relationship(
        "AttendanceRecord", backref="student", lazy=True
    )


class Lecturer(db.Model):
    __tablename__ = "lecturers"
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.String(32), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(20))  # Dr., Prof., Mr., Ms., Mrs.
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    courses = db.relationship("Course", backref="lecturer", lazy=True)


# ---------------------------------------------------------------------------
# Academic offerings
# ---------------------------------------------------------------------------
class Course(db.Model):
    __tablename__ = "courses"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(15), unique=True, nullable=False)  # e.g. CSCD 415
    title = db.Column(db.String(200), nullable=False)
    credit_hours = db.Column(db.Integer, default=3)
    semester = db.Column(db.Integer, default=1)  # 1 or 2
    academic_year = db.Column(db.String(15))  # '2025/2026'
    lecturer_id = db.Column(db.Integer, db.ForeignKey("lecturers.id"))
    sessions = db.relationship("ClassSession", backref="course", lazy=True)
    registrations = db.relationship("CourseRegistration", backref="course", lazy=True)


class CourseRegistration(db.Model):
    __tablename__ = "course_registrations"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("student_id", "course_id"),)


class ClassSession(db.Model):
    __tablename__ = "class_sessions"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    session_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    venue = db.Column(db.String(120))
    device_id = db.Column(db.Integer, db.ForeignKey("hik_devices.id"))
    is_open = db.Column(db.Boolean, default=False)  # lecturer can manually open/close
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    attendance_records = db.relationship(
        "AttendanceRecord", backref="session", lazy=True
    )


class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey("class_sessions.id"), nullable=False
    )
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    status = db.Column(db.String(15), default="absent")  # present, late, absent, excused
    check_in_time = db.Column(db.DateTime)
    similarity_score = db.Column(db.Float)  # 0..1 — from terminal recognition
    source = db.Column(db.String(20), default="terminal")  # terminal, manual, override
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("session_id", "student_id"),)


# ---------------------------------------------------------------------------
# Hardware & integration
# ---------------------------------------------------------------------------
class HikDevice(db.Model):
    __tablename__ = "hik_devices"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)  # e.g. "Lecture Hall A"
    model = db.Column(db.String(40), default="DS-K1T323MBFWX-E1")
    serial_no = db.Column(db.String(80))
    ip_address = db.Column(db.String(45), nullable=False)
    port = db.Column(db.Integer, default=80)
    username = db.Column(db.String(40), default="admin")
    password = db.Column(db.String(80))  # stored only because student project; in prod use a secret store
    # Network type the device is connected over (Wi-Fi or Ethernet/PoE).
    # Both reach our app over IP — this is just for UI / inventory.
    connection_type = db.Column(db.String(15), default="wifi")  # 'wifi' | 'ethernet' | 'poe'
    wifi_ssid = db.Column(db.String(80))
    last_seen = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    sessions = db.relationship("ClassSession", backref="device", lazy=True)


class EnrollmentLog(db.Model):
    __tablename__ = "enrollment_logs"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"))
    device_id = db.Column(db.Integer, db.ForeignKey("hik_devices.id"))
    action = db.Column(db.String(20))  # 'add', 'update', 'delete'
    success = db.Column(db.Boolean, default=False)
    response_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class EventLog(db.Model):
    __tablename__ = "event_logs"
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("hik_devices.id"))
    employee_id_seen = db.Column(db.String(32), index=True)
    similarity = db.Column(db.Float)
    occurred_at = db.Column(db.DateTime, default=datetime.utcnow)
    raw_payload = db.Column(db.Text)
    matched_session_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"))
    processed = db.Column(db.Boolean, default=False)


# ---------------------------------------------------------------------------
# UTAUT survey (for the Marketing teammates' acceptance study)
# ---------------------------------------------------------------------------
class SurveyResponse(db.Model):
    """
    Stores responses to the UTAUT2 acceptance instrument administered to
    UPSA students and lecturers as part of Chapter 4's non-IT evaluation.
    """
    __tablename__ = "survey_responses"
    id = db.Column(db.Integer, primary_key=True)
    respondent_role = db.Column(db.String(20))  # 'student', 'lecturer'
    age_band = db.Column(db.String(15))
    gender = db.Column(db.String(10))
    # 7-point Likert items (1=Strongly Disagree .. 7=Strongly Agree)
    pe1 = db.Column(db.Integer)  # Performance Expectancy
    pe2 = db.Column(db.Integer)
    pe3 = db.Column(db.Integer)
    ee1 = db.Column(db.Integer)  # Effort Expectancy
    ee2 = db.Column(db.Integer)
    ee3 = db.Column(db.Integer)
    si1 = db.Column(db.Integer)  # Social Influence
    si2 = db.Column(db.Integer)
    fc1 = db.Column(db.Integer)  # Facilitating Conditions
    fc2 = db.Column(db.Integer)
    pc1 = db.Column(db.Integer)  # Privacy Concern
    pc2 = db.Column(db.Integer)
    bi1 = db.Column(db.Integer)  # Behavioural Intention
    bi2 = db.Column(db.Integer)
    open_comment = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
