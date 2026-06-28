"""
Super Admin — system configuration, terminal management, audit logs.
"""

from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from ..extensions import db
from ..models import HikDevice, EnrollmentLog, EventLog, User
from ..services.hikvision_client import HikvisionTerminal

bp = Blueprint("superadmin", __name__, template_folder="../templates/super")


def super_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "super":
            abort(403)
        return f(*args, **kwargs)
    return decorated


@bp.route("/")
@login_required
@super_required
def dashboard():
    devices = HikDevice.query.all()
    users = User.query.count()
    enroll_recent = EnrollmentLog.query.order_by(EnrollmentLog.created_at.desc()).limit(20).all()
    events_recent = EventLog.query.order_by(EventLog.occurred_at.desc()).limit(20).all()
    return render_template("super_dashboard.html",
                           devices=devices, users=users,
                           enroll_recent=enroll_recent, events_recent=events_recent)


@bp.route("/devices/add", methods=["GET", "POST"])
@login_required
@super_required
def device_add():
    if request.method == "POST":
        d = HikDevice(
            name=request.form["name"],
            model=request.form.get("model", "DS-K1T323MBFWX-E1"),
            ip_address=request.form["ip_address"],
            port=int(request.form.get("port", 80)),
            username=request.form.get("username", "admin"),
            password=request.form.get("password", ""),
            connection_type=request.form.get("connection_type", "wifi"),
            wifi_ssid=request.form.get("wifi_ssid") or None,
            is_active=True,
        )
        db.session.add(d)
        db.session.commit()
        flash(f"Device {d.name} registered.", "success")
        return redirect(url_for("superadmin.dashboard"))
    return render_template("super_device_add.html")


@bp.route("/devices/<int:device_id>/probe")
@login_required
@super_required
def device_probe(device_id):
    d = HikDevice.query.get_or_404(device_id)
    term = HikvisionTerminal(
        host=d.ip_address, port=d.port,
        username=d.username, password=d.password,
        simulate=current_app.config.get("HIKVISION_SIMULATE", False),
    )
    info = term.get_device_info()
    if info:
        flash(f"Device online — {info.get('model')} / {info.get('serialNumber')}", "success")
    else:
        flash("Device unreachable. Check IP, network, credentials.", "danger")
    return redirect(url_for("superadmin.dashboard"))


@bp.route("/devices/<int:device_id>/register-listener", methods=["POST"])
@login_required
@super_required
def device_register_listener(device_id):
    d = HikDevice.query.get_or_404(device_id)
    term = HikvisionTerminal(
        host=d.ip_address, port=d.port,
        username=d.username, password=d.password,
        simulate=current_app.config.get("HIKVISION_SIMULATE", False),
    )
    listener_url = (f"http://{request.host_url.split('://')[1].rstrip('/')}"
                    f"{current_app.config['EVENT_LISTENER_PATH']}")
    ok, msg = term.register_event_listener(listener_url)
    if ok:
        flash(f"Listener registered: {listener_url}", "success")
    else:
        flash(f"Failed to register listener: {msg}", "danger")
    return redirect(url_for("superadmin.dashboard"))
