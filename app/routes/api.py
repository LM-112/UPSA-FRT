"""
Public-facing API blueprint.

The single most important endpoint is the Hikvision event listener:

    POST /api/v1/events/hik

The DS-K1T342MFX-E1 will be configured (via super-admin) to push every face
recognition event to this URL. We accept either JSON or multipart form-data
(Hikvision sends multipart when the event includes a snapshot).
"""

import json
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from ..extensions import db
from ..models import HikDevice
from ..services.attendance_engine import process_recognition_event

bp = Blueprint("api", __name__)


def _parse_hik_event(payload: dict) -> dict | None:
    """
    Hikvision pushes a JSON envelope along the lines of:
        {
          "ipAddress": "192.168.1.64",
          "eventType": "AccessControllerEvent",
          "AccessControllerEvent": {
              "majorEventType": 5,
              "subEventType": 75,
              "employeeNoString": "10182765",
              "name": "ANNAN ESTHER",
              "currentVerifyMode": "face",
              "similarity": 0.94,
              "type": 75,
              ...
          },
          "dateTime": "2026-04-29T13:45:32+00:00"
        }
    Returns a flat dict {employee_id, similarity, occurred_at, ip}.
    """
    try:
        evt = payload.get("AccessControllerEvent") or {}
        if not evt and "eventType" in payload:
            evt = payload
        emp = evt.get("employeeNoString") or evt.get("employeeNo")
        if emp is None:
            return None
        sim = evt.get("similarity")
        if sim is not None and float(sim) > 1:
            sim = float(sim) / 100.0  # device may report 0..100
        when = payload.get("dateTime") or evt.get("dateTime")
        try:
            occurred_at = datetime.fromisoformat(when.replace("Z", "+00:00")) if when else datetime.utcnow()
            occurred_at = occurred_at.replace(tzinfo=None)
        except Exception:
            occurred_at = datetime.utcnow()
        return {
            "employee_id": str(emp),
            "similarity": float(sim) if sim is not None else None,
            "occurred_at": occurred_at,
            "ip": payload.get("ipAddress"),
        }
    except Exception:
        return None


@bp.route("/events/hik", methods=["POST"])
def hik_event():
    """
    Endpoint for the Hikvision DS-K1T342MFX-E1 to push recognition events to.
    """
    raw_text = ""
    payload = {}
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        raw_text = json.dumps(payload)
    else:
        # Multipart with a 'event_log' JSON part + image parts
        if "event_log" in request.form:
            raw_text = request.form["event_log"]
            try:
                payload = json.loads(raw_text)
            except Exception:
                payload = {}
        else:
            raw_text = request.data.decode("utf-8", errors="ignore")
            try:
                payload = json.loads(raw_text)
            except Exception:
                payload = {}

    parsed = _parse_hik_event(payload)
    if parsed is None:
        return jsonify({"ok": False, "reason": "unparseable"}), 400

    # Resolve device (best-effort)
    device = HikDevice.query.filter_by(ip_address=parsed.get("ip") or "").first()

    result = process_recognition_event(
        employee_id=parsed["employee_id"],
        similarity=parsed["similarity"] or 0.0,
        occurred_at=parsed["occurred_at"],
        device_id=device.id if device else None,
        raw_payload=raw_text,
    )
    return jsonify(result)


@bp.route("/health")
def health():
    return jsonify({"ok": True, "version": "1.0.0"})
