"""
Seed the database with realistic UPSA demo data so the app can be demoed
without a populated production environment.

Run:
    python run.py --seed

Creates:
    - Faculty of IT & Communication Studies + Marketing
    - Departments: IT Studies, Marketing
    - Programmes: BSc IT Management, BSc Marketing
    - 1 Super Admin, 1 Admin, 2 Lecturers, 30 Students
    - 4 Courses (IT + Marketing), 3 sessions each (yesterday, today, tomorrow)
    - PLUS 2 "happening right now" demo sessions (one IT, one Marketing) that
      start 15 minutes ago and end 2 hours from now — guaranteeing that a
      live face recognition or simulated event always lands cleanly during
      the panel defence regardless of the wall-clock time.
    - 1 Hikvision Device
    - Course registrations
"""

from datetime import date, time, datetime, timedelta
import random
from app.extensions import db
from app.models import (
    User, Faculty, Department, Programme, Student, Lecturer,
    Course, ClassSession, CourseRegistration, HikDevice,
)


def _now_window():
    """
    Return (session_date, start_time, end_time) for a class session that's
    'happening right now' — i.e. started 15 minutes ago and ends 2 hours
    from now. Caps end_time at 23:59 to avoid crossing midnight.
    """
    now = datetime.now()
    start_dt = now - timedelta(minutes=15)
    end_dt = now + timedelta(hours=2)
    # If end_dt would cross midnight, clamp to 23:59 of the start date so
    # session_date / start_time / end_time stay consistent.
    if end_dt.date() != start_dt.date():
        end_dt = datetime.combine(start_dt.date(), time(23, 59))
    return start_dt.date(), start_dt.time().replace(microsecond=0), end_dt.time().replace(microsecond=0)


GHANAIAN_FIRST = ["Kwame", "Akua", "Yaw", "Esi", "Kofi", "Ama", "Kojo", "Adwoa",
                  "Kwaku", "Akosua", "Kwadwo", "Afia", "Yaa", "Naa", "Abena",
                  "Nana", "Kweku", "Mansa", "Efua", "Adjoa"]
GHANAIAN_LAST = ["Mensah", "Owusu", "Asante", "Boateng", "Frimpong", "Adjei",
                 "Annan", "Quaye", "Tetteh", "Darko", "Agyemang", "Osei",
                 "Bediako", "Acheampong", "Ofori", "Sarpong", "Amoah",
                 "Twum", "Kyei", "Wiredu"]

# UPSA halls of residence
UPSA_HALLS = ["Yaa Asantewaa", "Africa", "Independence", "Republic", "Unity"]


def seed_database():
    print("Seeding UPSA demo data…")

    # --- Faculties / Departments / Programmes --------------------------------
    f_it = Faculty(name="Faculty of Information Technology & Communication Studies",
                   code="FITCS")
    f_mk = Faculty(name="Faculty of Management Studies", code="FMS")
    db.session.add_all([f_it, f_mk]); db.session.flush()

    d_it = Department(name="Department of Information Technology Studies",
                      code="DITS", faculty_id=f_it.id)
    d_mk = Department(name="Department of Marketing", code="DMKT", faculty_id=f_mk.id)
    db.session.add_all([d_it, d_mk]); db.session.flush()

    p_it = Programme(name="BSc Information Technology Management",
                     code="BIT", department_id=d_it.id)
    p_mk = Programme(name="BSc Marketing", code="BMK", department_id=d_mk.id)
    db.session.add_all([p_it, p_mk]); db.session.flush()

    # --- Users ---------------------------------------------------------------
    super_user = User(email="super@upsa.edu.gh", full_name="System Super Admin", role="super")
    super_user.set_password("Super@2026")

    admin_user = User(email="admin@upsa.edu.gh", full_name="Margaret Boadu", role="admin")
    admin_user.set_password("Admin@2026")

    db.session.add_all([super_user, admin_user]); db.session.flush()

    # --- Lecturers -----------------------------------------------------------
    lec1_u = User(email="kowusu@upsa.edu.gh", full_name="Kwame Owusu", role="lecturer")
    lec1_u.set_password("Lecturer@2026")
    lec2_u = User(email="aboateng@upsa.edu.gh", full_name="Ama Boateng", role="lecturer")
    lec2_u.set_password("Lecturer@2026")
    db.session.add_all([lec1_u, lec2_u]); db.session.flush()

    lec1 = Lecturer(staff_id="UPSA/IT/0042", title="Dr.", full_name=lec1_u.full_name,
                    department_id=d_it.id, user_id=lec1_u.id)
    lec2 = Lecturer(staff_id="UPSA/MKT/0017", title="Dr.", full_name=lec2_u.full_name,
                    department_id=d_mk.id, user_id=lec2_u.id)
    db.session.add_all([lec1, lec2]); db.session.flush()

    # --- Courses -------------------------------------------------------------
    courses = [
        Course(code="ITM 412", title="Information Systems Security",
               credit_hours=3, semester=2, academic_year="2025/2026",
               lecturer_id=lec1.id),
        Course(code="ITM 416", title="Mobile Application Development",
               credit_hours=3, semester=2, academic_year="2025/2026",
               lecturer_id=lec1.id),
        Course(code="MKT 410", title="Digital Marketing Strategy",
               credit_hours=3, semester=2, academic_year="2025/2026",
               lecturer_id=lec2.id),
        Course(code="MKT 414", title="Consumer Behaviour",
               credit_hours=3, semester=2, academic_year="2025/2026",
               lecturer_id=lec2.id),
    ]
    db.session.add_all(courses); db.session.flush()

    # --- Students -----------------------------------------------------------
    random.seed(42)
    students = []

    # 1) Real UPSA student from the sample ID card (Donkor Amponsah Lawrence,
    #    BSc Marketing, ID 10300137, Yaa Asantewaa Hall, Entry Level 100).
    real_email = "10300137@students.upsa.edu.gh"
    real_user = User(email=real_email,
                     full_name="Donkor Amponsah Lawrence", role="student")
    real_user.set_password("Student@2026")
    db.session.add(real_user); db.session.flush()
    real_student = Student(
        employee_id="10300137",
        index_number="10300137",
        full_name="Donkor Amponsah Lawrence",
        gender="male",
        nationality="Ghanaian",
        level=100,
        entry_level=100,
        hall="Yaa Asantewaa",
        programme_id=p_mk.id,
        user_id=real_user.id,
        consent_given=True,
        consent_date=datetime.utcnow(),
        enrolled_on_terminal=False,
    )
    db.session.add(real_student); db.session.flush()
    students.append(real_student)

    # 2) Synthetic students to populate the dashboard.
    for i in range(30):
        first = random.choice(GHANAIAN_FIRST)
        last = random.choice(GHANAIAN_LAST)
        idx = f"1018{2700 + i:04d}"
        prog = p_it if i < 18 else p_mk
        u = User(email=f"{idx}@students.upsa.edu.gh",
                 full_name=f"{first} {last}", role="student")
        u.set_password("Student@2026")
        db.session.add(u); db.session.flush()
        s = Student(
            employee_id=idx,
            index_number=idx,
            full_name=f"{first} {last}",
            gender=random.choice(["male", "female"]),
            nationality="Ghanaian",
            level=400,
            entry_level=100,
            hall=random.choice(UPSA_HALLS),
            programme_id=prog.id,
            user_id=u.id,
            consent_given=True,
            consent_date=datetime.utcnow(),
            enrolled_on_terminal=False,
        )
        db.session.add(s)
        students.append(s)
    db.session.flush()

    # --- Course registrations -------------------------------------------------
    # IT students take both ITM courses; MKT students take both MKT courses.
    for s in students:
        is_it = s.programme_id == p_it.id
        for c in courses:
            if (is_it and c.code.startswith("ITM")) or \
               (not is_it and c.code.startswith("MKT")):
                db.session.add(CourseRegistration(student_id=s.id, course_id=c.id))

    # --- Device --------------------------------------------------------------
    # The actual hardware in hand is a Hikvision MinMoe DS-K1T323MBFWX-E1
    # (W = Wi-Fi capable, F = Fingerprint, IP65, deep-learning recognition).
    device = HikDevice(
        name="Main Lecture Hall – DS-K1T323MBFWX-E1",
        model="DS-K1T323MBFWX-E1",
        serial_no="GM6647437",
        ip_address="192.168.1.64",
        port=80, username="admin", password="Upsa@2026",
        connection_type="wifi",
        wifi_ssid="UPSA-Campus-WiFi",
        is_active=True,
    )
    db.session.add(device); db.session.flush()

    # --- Class sessions: yesterday, today, tomorrow for each course ----------
    today = date.today()
    times = [(time(8, 0), time(10, 0)),
             (time(11, 0), time(13, 0)),
             (time(14, 0), time(16, 0))]
    for ci, c in enumerate(courses):
        for di, d_offset in enumerate([-1, 0, 1]):
            sd = today + timedelta(days=d_offset)
            st_start, st_end = times[ci % len(times)]
            db.session.add(ClassSession(
                course_id=c.id, session_date=sd,
                start_time=st_start, end_time=st_end,
                venue="Main Lecture Hall", device_id=device.id,
                is_open=(d_offset == 0),
            ))

    # --- Demo "happening right now" sessions ---------------------------------
    # One per programme so both IT and Marketing students can demo live.
    # These guarantee any face recognition / simulated event during the
    # panel defence lands cleanly, regardless of the time of day.
    now_date, now_start, now_end = _now_window()
    for c in (courses[0], courses[2]):  # ITM 412 (IT) and MKT 410 (Marketing)
        db.session.add(ClassSession(
            course_id=c.id,
            session_date=now_date,
            start_time=now_start,
            end_time=now_end,
            venue="Main Lecture Hall (Live Demo)",
            device_id=device.id,
            is_open=True,
            notes="Auto-generated demo session — active for 2 hours from seed time.",
        ))

    db.session.commit()
    print(f"  Faculties: 2, Departments: 2, Programmes: 2")
    print(f"  Users: {User.query.count()}  Students: {Student.query.count()}")
    print(f"  Courses: {Course.query.count()}  Sessions: {ClassSession.query.count()}")
    print(f"  Live demo sessions active until {now_end.strftime('%H:%M')} today.")
    print()
    print("Demo logins:")
    print("  super@upsa.edu.gh                / Super@2026")
    print("  admin@upsa.edu.gh                / Admin@2026")
    print("  kowusu@upsa.edu.gh               / Lecturer@2026  (IT Lecturer)")
    print("  aboateng@upsa.edu.gh             / Lecturer@2026  (Marketing Lecturer)")
    print("  10300137@students.upsa.edu.gh    / Student@2026  (Donkor Amponsah Lawrence — real card)")
    print("  10182700@students.upsa.edu.gh    / Student@2026  (synthetic IT student)")
