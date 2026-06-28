"""
UPSA Face Recognition Attendance System — Configuration

This module centralises every tunable parameter so the system can be moved
from a developer laptop (SQLite, default Hikvision IP) to a production UPSA
server (PostgreSQL, real terminal IPs) by editing only environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _resolve_data_dir() -> Path:
    """
    Choose a writable directory for the SQLite database.

    On Windows, the project folder is often under Documents (and therefore
    OneDrive-synced), which intermittently blocks SQLite from creating
    files. To avoid that, we default to %LOCALAPPDATA%\\UpsaFrt — never
    synced, always writable. On macOS/Linux we keep the local instance
    folder (no equivalent OneDrive issue).
    """
    if os.name == "nt":  # Windows
        local = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if local:
            return Path(local) / "UpsaFrt"
    return BASE_DIR / "instance"


INSTANCE_DIR = _resolve_data_dir()
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

# Use forward slashes for the SQLite URI — backslashes break SQLAlchemy's URL
# parser on Windows when the path contains spaces or a drive-letter colon.
_DEFAULT_DB_PATH = (INSTANCE_DIR / "upsa_frt.db").as_posix()


class Config:
    # --- Flask core --------------------------------------------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "upsa-frt-dev-key-change-in-production")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8  # 8 hours

    # --- Database ----------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{_DEFAULT_DB_PATH}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Uploads -----------------------------------------------------------
    UPLOAD_FOLDER = BASE_DIR / "app" / "static" / "uploads"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB max upload (face photo)

    # --- Hikvision DS-K1T342MFX-E1 terminal --------------------------------
    # The terminal speaks ISAPI over HTTP with HTTP Digest authentication.
    # Default-out-of-the-box values per the user manual:
    HIKVISION_TERMINAL_IP = os.getenv("HIKVISION_TERMINAL_IP", "192.0.0.64")
    HIKVISION_TERMINAL_PORT = int(os.getenv("HIKVISION_TERMINAL_PORT", "80"))
    HIKVISION_USERNAME = os.getenv("HIKVISION_USERNAME", "admin")
    HIKVISION_PASSWORD = os.getenv("HIKVISION_PASSWORD", "Upsa@2026")
    HIKVISION_TIMEOUT = int(os.getenv("HIKVISION_TIMEOUT", "10"))

    # --- Event listener ----------------------------------------------------
    # The terminal can be configured to push recognition events (alarm/event
    # notification) to a listener URL. We expose one inside the Flask app at
    # /api/v1/events/hik for the device to POST to.
    EVENT_LISTENER_HOST = os.getenv("EVENT_LISTENER_HOST", "0.0.0.0")
    EVENT_LISTENER_PORT = int(os.getenv("PORT", os.getenv("EVENT_LISTENER_PORT", "5000")))
    EVENT_LISTENER_PATH = "/api/v1/events/hik"

    # --- UPSA-specific defaults --------------------------------------------
    INSTITUTION_NAME = "University of Professional Studies, Accra"
    INSTITUTION_SHORT = "UPSA"
    ACADEMIC_YEAR = os.getenv("ACADEMIC_YEAR", "2025/2026")

    # --- Attendance policy --------------------------------------------------
    # Window (minutes) before scheduled session start during which the device
    # may mark attendance for that session.
    ATTENDANCE_OPEN_BEFORE_MIN = 15
    # Window (minutes) after start during which a student is still 'present'.
    ATTENDANCE_PRESENT_GRACE_MIN = 15
    # After grace, until end of session, the student is marked 'late'.
    # After the session ends, the student is marked 'absent'.

    # Minimum recognition similarity score (returned by the terminal) to
    # accept the recognition as valid.
    MIN_RECOGNITION_SIMILARITY = float(os.getenv("MIN_RECOGNITION_SIMILARITY", "0.85"))
    HIKVISION_SIMULATE = os.getenv("HIKVISION_SIMULATE", "true").lower() == "true"


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
