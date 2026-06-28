# UPSA Face Recognition Attendance System

A Flask + SQLite application that integrates with the **Hikvision DS-K1T323MBFWX-E1**
face recognition terminal to automate student attendance at the
**University of Professional Studies, Accra**.

## Architecture

```
+--------------------+           HTTP / Digest         +-----------------------+
|  Hikvision         |  <===========================>  |  Flask Application    |
|  DS-K1T323MBFWX-E1   |       ISAPI (XML/JSON)          |  (Python 3.10+)       |
|                    |                                  |                       |
|  - Face detection  |  -- POST event push -->         |  - Hikvision client   |
|  - Face matching   |     /api/v1/events/hik          |  - Event listener     |
|  - 1500-face DB    |                                  |  - Attendance engine  |
+--------------------+                                  |  - 4 role dashboards  |
                                                         |  - Reports (Excel)    |
                                                         +-----------+-----------+
                                                                     |
                                                                     v
                                                            +--------+--------+
                                                            |  SQLite (dev)   |
                                                            |  PostgreSQL     |
                                                            |  (production)   |
                                                            +-----------------+
```

## Roles

| Role | Capabilities |
|------|-------------|
| Super Admin | Register/probe terminals, configure event listener, view audit logs |
| Department Admin | Manage students, courses, lecturers; trigger face enrolment; export reports |
| Lecturer | Open/close session, live attendance view, manual override, export Excel |
| Student | View personal attendance, course-by-course breakdown |

## Setup

```bash
# 1. Create venv (recommended)
python -m venv venv
source venv/bin/activate          # macOS / Linux
venv\Scripts\activate             # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialise database with realistic UPSA demo data
python run.py --seed

# 4. Run the dev server
python run.py
```

Open `http://localhost:5000`.

### Demo Logins

| Role        | Email                               | Password        |
|-------------|-------------------------------------|-----------------|
| Super Admin | super@upsa.edu.gh                   | Super@2026      |
| Admin       | admin@upsa.edu.gh                   | Admin@2026      |
| Lecturer    | kowusu@upsa.edu.gh                  | Lecturer@2026   |
| Student     | 10182700@students.upsa.edu.gh       | Student@2026    |

## Configuring the Hikvision Terminal

1. Power up the DS-K1T323MBFWX-E1 and complete first-boot activation (set `admin` password).
2. Note the device IP (default `192.0.0.64`); set a static IP on your campus subnet.
3. In the application, log in as **Super Admin** → **Register Terminal** with that IP.
4. Click **Probe** to verify connectivity.
5. Click **Register Listener** — this tells the device to POST every recognition
   event to `http://<your-server>:5000/api/v1/events/hik`.

## Testing

```bash
pytest tests/ -q
```

15 tests cover the attendance engine, Hikvision client (simulate mode),
and HTTP routes.

## Running Without the Physical Device

Set `HIKVISION_SIMULATE=1` (or pass `simulate=True` to `HikvisionTerminal()`)
to run the entire app without a terminal — useful for development and panel rehearsal.
