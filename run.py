"""
Entry point for running the UPSA FRT Attendance System in development.

Usage:
    python run.py                # starts Flask dev server on :5000
    python run.py --init-db      # initialises database schema
    python run.py --seed         # loads demo UPSA students/courses/lecturers
    python run.py --probe        # tests connectivity to the Hikvision terminal
"""

import sys
from app import create_app
from app.extensions import db
from scripts.seed_demo import seed_database
from app.services.hikvision_client import HikvisionTerminal

app = create_app()


def init_db():
    with app.app_context():
        db.create_all()
        print("[OK] Database schema created.")


def probe_terminal():
    cfg = app.config
    term = HikvisionTerminal(
        host=cfg["HIKVISION_TERMINAL_IP"],
        port=cfg["HIKVISION_TERMINAL_PORT"],
        username=cfg["HIKVISION_USERNAME"],
        password=cfg["HIKVISION_PASSWORD"],
        timeout=cfg["HIKVISION_TIMEOUT"],
    )
    info = term.get_device_info()
    if info:
        print("[OK] Terminal reachable.")
        for k, v in info.items():
            print(f"  {k}: {v}")
    else:
        print("[FAIL] Could not reach terminal at "
              f"{cfg['HIKVISION_TERMINAL_IP']}:{cfg['HIKVISION_TERMINAL_PORT']}")


if __name__ == "__main__":
    if "--init-db" in sys.argv:
        init_db()
    elif "--seed" in sys.argv:
        with app.app_context():
            db.create_all()
            seed_database()
    elif "--probe" in sys.argv:
        probe_terminal()
    else:
        with app.app_context():
            db.create_all()
        app.run(
            host=app.config["EVENT_LISTENER_HOST"],
            port=app.config["EVENT_LISTENER_PORT"],
            debug=True,
        )
