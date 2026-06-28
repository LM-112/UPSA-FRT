"""
UPSA Face Recognition Attendance System
=======================================

A Flask application that integrates with the Hikvision DS-K1T342MFX-E1
face recognition terminal to automate student attendance at the
University of Professional Studies, Accra.

Architecture (4-layer, per Chapter 3 of the thesis):
    Input Layer        — Hikvision DS-K1T342MFX-E1 terminal
    Processing Layer   — Hikvision on-device FaceNet pipeline + our event mapper
    Data Layer         — SQLite (dev) / PostgreSQL (prod) via SQLAlchemy ORM
    Presentation Layer — Flask + Bootstrap dashboards (4 roles)
"""

from flask import Flask, redirect, url_for
from .extensions import db, login_manager
from config import Config


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_class)

    # Ensure runtime directories exist. (The DB instance folder is created
    # in config.py so it's ready before SQLAlchemy initialises.)
    try:
        (app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    except OSError:
        # OneDrive can transiently block folder creation; ignore if it
        # already exists or we can fall back to a temp directory.
        pass

    db.init_app(app)
    login_manager.init_app(app)

    # Register user-loader (Flask-Login)
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --- Blueprints --------------------------------------------------------
    from .routes.auth import bp as auth_bp
    from .routes.admin import bp as admin_bp
    from .routes.lecturer import bp as lecturer_bp
    from .routes.student import bp as student_bp
    from .routes.superadmin import bp as superadmin_bp
    from .routes.api import bp as api_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(lecturer_bp, url_prefix="/lecturer")
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(superadmin_bp, url_prefix="/super")
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    @app.context_processor
    def inject_globals():
        return {
            "INSTITUTION_NAME": app.config["INSTITUTION_NAME"],
            "INSTITUTION_SHORT": app.config["INSTITUTION_SHORT"],
            "ACADEMIC_YEAR": app.config["ACADEMIC_YEAR"],
        }

    return app
