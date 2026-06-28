"""
Generate the architecture, ER, use-case, sequence and deployment diagrams
referenced in Chapter 3 of the thesis. Output is a folder of PNGs.

Run:
    python scripts/build_diagrams.py

Output folder:
    assets/diagrams/
"""

from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, ConnectionPatch
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)

UPSA_NAVY = "#003366"
UPSA_GOLD = "#ffb300"
GREY_BG = "#f4f6f8"
TEXT_DARK = "#1c1c1c"
ACCENT = "#4a7ca8"


# --------------------------------------------------------------------- helpers
def box(ax, x, y, w, h, label, *, fill=GREY_BG, edge=UPSA_NAVY,
        text_color=TEXT_DARK, fontsize=10, bold=False):
    fancy = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.05",
        linewidth=1.4, edgecolor=edge, facecolor=fill,
    )
    ax.add_patch(fancy)
    ax.text(x + w / 2, y + h / 2, label,
            ha="center", va="center", fontsize=fontsize,
            color=text_color, weight=("bold" if bold else "normal"),
            wrap=True)


def arrow(ax, x1, y1, x2, y2, *, color=UPSA_NAVY, lw=1.4, label=None,
          text_offset=(0.05, 0.05)):
    a = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=14,
        color=color, linewidth=lw,
    )
    ax.add_patch(a)
    if label:
        mx, my = (x1 + x2) / 2 + text_offset[0], (y1 + y2) / 2 + text_offset[1]
        ax.text(mx, my, label, fontsize=8, color=color, ha="center")


def setup_canvas(width=12, height=8, title=None):
    fig, ax = plt.subplots(figsize=(width, height), dpi=150)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=14, weight="bold",
                     color=UPSA_NAVY, pad=15)
    return fig, ax


# --------------------------------------------------------------------- 1. SYSTEM ARCHITECTURE
def diagram_architecture():
    fig, ax = setup_canvas(
        13, 9,
        "Figure 3.1 — Four-Layer System Architecture")

    # Layer bands
    bands = [
        (7.4, "Presentation Layer", "#e8edf3"),
        (5.5, "Processing Layer",   "#eef4f8"),
        (3.6, "Data Layer",         "#f6efe6"),
        (1.7, "Input Layer",        "#fff4d9"),
    ]
    for y, label, fill in bands:
        ax.add_patch(FancyBboxPatch((0.4, y), 12.2, 1.5,
                                    boxstyle="round,pad=0.02,rounding_size=0.05",
                                    facecolor=fill, edgecolor="#cccccc",
                                    linewidth=0.8))
        ax.text(0.7, y + 1.3, label, fontsize=11, weight="bold",
                color=UPSA_NAVY)

    # Presentation
    box(ax, 1.0, 7.7, 2.4, 0.9, "Super Admin\nDashboard")
    box(ax, 4.0, 7.7, 2.4, 0.9, "Admin\nDashboard")
    box(ax, 7.0, 7.7, 2.4, 0.9, "Lecturer\nLive View")
    box(ax, 10.0, 7.7, 2.4, 0.9, "Student\nDashboard")

    # Processing
    box(ax, 1.0, 5.8, 2.6, 0.9, "Flask Routes\n(Blueprints × 6)")
    box(ax, 4.2, 5.8, 2.6, 0.9, "Attendance\nEngine")
    box(ax, 7.4, 5.8, 2.6, 0.9, "Hikvision\nISAPI Client")
    box(ax, 10.6, 5.8, 1.8, 0.9, "Event\nListener")

    # Data
    box(ax, 1.0, 3.9, 3.0, 0.9, "SQLAlchemy ORM",
        fill="#fff", edge=ACCENT)
    box(ax, 4.6, 3.9, 3.6, 0.9, "SQLite (dev)\n/ PostgreSQL (prod)",
        fill="#fff", edge=ACCENT)
    box(ax, 8.8, 3.9, 3.6, 0.9, "13 Tables incl.\nUser, Student, AttendanceRecord",
        fill="#fff", edge=ACCENT, fontsize=9)

    # Input
    box(ax, 1.0, 2.0, 4.5, 1.0,
        "Hikvision MinMoe DS-K1T323MBFWX-E1",
        fill="#fff8e1", edge=UPSA_GOLD, bold=True, fontsize=11)
    box(ax, 6.0, 2.0, 2.4, 1.0, "On-device\nFaceNet Pipeline",
        fill="#fff8e1", edge=UPSA_GOLD)
    box(ax, 8.7, 2.0, 1.7, 1.0, "Wi-Fi /\nPoE",
        fill="#fff8e1", edge=UPSA_GOLD)
    box(ax, 10.7, 2.0, 1.7, 1.0, "Fingerprint\nReader",
        fill="#fff8e1", edge=UPSA_GOLD)

    # Vertical arrows between layers
    arrow(ax, 6.5, 7.7, 6.5, 6.7)
    arrow(ax, 6.5, 5.8, 6.5, 4.8)
    arrow(ax, 6.5, 3.9, 6.5, 3.0)

    # Side legend / caption
    ax.text(6.5, 0.6,
            "Recognition events flow upward (Input → Processing → Data → Presentation).\n"
            "Enrolment commands flow downward (Presentation → Processing → ISAPI → Terminal).",
            fontsize=9, ha="center", style="italic", color="#444")

    plt.savefig(OUT / "01_system_architecture.png",
                bbox_inches="tight", dpi=200, facecolor="white")
    plt.close()
    print("  ✓ 01_system_architecture.png")


# --------------------------------------------------------------------- 2. USE CASE
def diagram_use_case():
    fig, ax = setup_canvas(13, 9, "Figure 3.2 — Use Case Diagram")

    # System boundary
    ax.add_patch(FancyBboxPatch((3.2, 0.8), 6.6, 7.4,
                                 boxstyle="round,pad=0.02,rounding_size=0.1",
                                 facecolor="#f8fbfd", edgecolor=UPSA_NAVY,
                                 linewidth=1.6))
    ax.text(6.5, 8.0, "UPSA FRT Attendance System",
            ha="center", fontsize=12, weight="bold", color=UPSA_NAVY)

    # Use cases (ovals)
    use_cases = [
        (4.0, 7.0, 2.0, 0.6, "Enrol Face on Terminal"),
        (7.0, 7.0, 2.0, 0.6, "Open / Close Session"),
        (4.0, 6.1, 2.0, 0.6, "Receive Recognition Event"),
        (7.0, 6.1, 2.0, 0.6, "View Live Attendance"),
        (4.0, 5.2, 2.0, 0.6, "Record Attendance"),
        (7.0, 5.2, 2.0, 0.6, "Manual Override"),
        (4.0, 4.3, 2.0, 0.6, "Export Excel Report"),
        (7.0, 4.3, 2.0, 0.6, "View My Attendance"),
        (4.0, 3.4, 2.0, 0.6, "Manage Students"),
        (7.0, 3.4, 2.0, 0.6, "Manage Courses"),
        (4.0, 2.5, 2.0, 0.6, "Register Terminal"),
        (7.0, 2.5, 2.0, 0.6, "Configure Listener"),
        (5.5, 1.4, 2.0, 0.6, "Capture Consent"),
    ]
    for x, y, w, h, label in use_cases:
        oval = mpatches.Ellipse((x + w/2, y + h/2), w, h,
                                 facecolor="#fff8e1", edgecolor=UPSA_NAVY,
                                 linewidth=1.2)
        ax.add_patch(oval)
        ax.text(x + w/2, y + h/2, label, ha="center", va="center",
                fontsize=8.5, color=TEXT_DARK)

    # Actors (stick figures + label)
    def stick(ax, x, y, name):
        ax.plot([x, x], [y - 0.55, y - 0.95], color=UPSA_NAVY, lw=1.4)
        circle = mpatches.Circle((x, y - 0.4), 0.12,
                                  facecolor="white", edgecolor=UPSA_NAVY, lw=1.4)
        ax.add_patch(circle)
        ax.plot([x - 0.25, x + 0.25], [y - 0.7, y - 0.7],
                color=UPSA_NAVY, lw=1.4)
        ax.plot([x - 0.18, x, x + 0.18],
                [y - 1.15, y - 0.95, y - 1.15], color=UPSA_NAVY, lw=1.4)
        ax.text(x, y - 1.4, name, ha="center", fontsize=9.5,
                weight="bold", color=UPSA_NAVY)

    stick(ax, 1.5, 7.0, "Student")
    stick(ax, 1.5, 4.5, "Lecturer")
    stick(ax, 11.5, 7.0, "Admin")
    stick(ax, 11.5, 4.5, "Super\nAdmin")

    # Connections (lines from actors to use cases — kept light-touch)
    pairs = [
        (1.6, 6.6, 4.0, 7.3),    # Student → Enrol
        (1.6, 6.4, 4.0, 5.5),    # Student → Record
        (1.6, 6.2, 7.0, 4.6),    # Student → View My Attendance
        (1.6, 4.1, 7.0, 7.3),    # Lecturer → Open/Close
        (1.6, 4.0, 7.0, 6.4),    # Lecturer → View Live
        (1.6, 3.9, 7.0, 5.5),    # Lecturer → Manual Override
        (1.6, 3.8, 4.0, 4.6),    # Lecturer → Export
        (11.4, 6.6, 9.0, 3.7),   # Admin → Manage Students
        (11.4, 6.4, 9.0, 3.7),   # Admin → Manage Courses (overlap)
        (11.4, 6.2, 9.0, 4.6),   # Admin → Export
        (11.4, 4.1, 6.0, 2.8),   # Super → Register Terminal
        (11.4, 4.0, 9.0, 2.8),   # Super → Configure Listener
    ]
    for x1, y1, x2, y2 in pairs:
        ax.plot([x1, x2], [y1, y2], color="#888", lw=0.8)

    plt.savefig(OUT / "02_use_case.png",
                bbox_inches="tight", dpi=200, facecolor="white")
    plt.close()
    print("  ✓ 02_use_case.png")


# --------------------------------------------------------------------- 3. SEQUENCE / DATA FLOW
def diagram_sequence():
    fig, ax = setup_canvas(13, 9,
                           "Figure 3.3 — End-to-End Recognition Sequence")

    # Lifelines
    lanes = [
        (1.5, "Student", "#fff8e1"),
        (3.8, "DS-K1T323MBFWX-E1", "#e8edf3"),
        (6.3, "Flask Listener\n/api/v1/events/hik", "#eef4f8"),
        (8.6, "Attendance\nEngine", "#eef4f8"),
        (10.9, "SQLite DB", "#f6efe6"),
    ]
    top = 7.7
    bottom = 1.0
    for x, name, fill in lanes:
        # Header box
        ax.add_patch(FancyBboxPatch((x - 0.9, top), 1.8, 0.6,
                                     boxstyle="round,pad=0.02,rounding_size=0.05",
                                     facecolor=fill, edgecolor=UPSA_NAVY,
                                     linewidth=1.2))
        ax.text(x, top + 0.3, name, ha="center", va="center",
                fontsize=9, weight="bold", color=UPSA_NAVY)
        # Lifeline
        ax.plot([x, x], [top, bottom], linestyle="--",
                color="#aaa", lw=0.8)

    # Steps
    steps = [
        (1.5, 3.8, 7.0, "1. Approach terminal"),
        (3.8, 3.8, 6.4, "2. FaceNet match (1500-face library)"),
        (3.8, 6.3, 5.8, "3. POST recognition event\n(JSON: employeeNoString, similarity, dateTime)"),
        (6.3, 8.6, 5.0, "4. Resolve to student → active session"),
        (8.6, 10.9, 4.4, "5. Insert AttendanceRecord (idempotent)"),
        (10.9, 8.6, 3.8, "6. OK"),
        (8.6, 6.3, 3.2, "7. Return {ok, status: present/late}"),
        (6.3, 3.8, 2.6, "8. HTTP 200"),
        (3.8, 1.5, 2.0, "9. Green tick on screen"),
    ]
    for x1, x2, y, label in steps:
        if x1 < x2:
            arrow(ax, x1, y, x2, y, lw=1.3)
        else:
            arrow(ax, x1, y, x2, y, lw=1.3, color="#888")
        midx = (x1 + x2) / 2
        ax.text(midx, y + 0.18, label, ha="center", va="bottom",
                fontsize=8, color=TEXT_DARK)

    plt.savefig(OUT / "03_sequence.png",
                bbox_inches="tight", dpi=200, facecolor="white")
    plt.close()
    print("  ✓ 03_sequence.png")


# --------------------------------------------------------------------- 4. ER DIAGRAM
def diagram_er():
    fig, ax = setup_canvas(14, 10,
                           "Figure 3.4 — Entity-Relationship Diagram (Core Tables)")

    # Tables (entity boxes)
    entities = {
        "User": (1.0, 7.4, 2.5, 1.4, [
            "id PK", "email UK", "password_hash",
            "full_name", "role", "is_active"]),
        "Student": (4.5, 7.4, 2.8, 1.6, [
            "id PK", "employee_id UK", "index_number UK",
            "full_name", "level", "hall",
            "programme_id FK", "user_id FK"]),
        "Lecturer": (8.3, 7.4, 2.8, 1.4, [
            "id PK", "staff_id UK", "title", "full_name",
            "department_id FK", "user_id FK"]),
        "Programme": (12.0, 7.4, 1.6, 1.4, [
            "id PK", "name", "code",
            "department_id FK"]),
        "Course": (8.3, 4.8, 2.8, 1.6, [
            "id PK", "code UK", "title",
            "credit_hours", "semester",
            "lecturer_id FK"]),
        "ClassSession": (4.5, 4.8, 2.8, 1.6, [
            "id PK", "course_id FK",
            "session_date", "start_time",
            "end_time", "venue",
            "device_id FK", "is_open"]),
        "AttendanceRecord": (1.0, 4.8, 2.8, 1.6, [
            "id PK", "session_id FK",
            "student_id FK", "status",
            "check_in_time",
            "similarity_score", "source"]),
        "HikDevice": (1.0, 2.0, 2.8, 1.6, [
            "id PK", "name",
            "model", "serial_no",
            "ip_address", "port",
            "connection_type", "wifi_ssid"]),
        "EventLog": (4.5, 2.0, 2.8, 1.6, [
            "id PK", "device_id FK",
            "employee_id_seen",
            "similarity",
            "occurred_at",
            "matched_session_id FK"]),
        "EnrollmentLog": (8.3, 2.0, 2.8, 1.6, [
            "id PK", "student_id FK",
            "device_id FK", "action",
            "success", "response_text"]),
        "SurveyResponse": (12.0, 2.0, 1.6, 1.6, [
            "id PK", "respondent_role",
            "pe1..pe3", "ee1..ee3",
            "si1..si2", "fc1..fc2",
            "pc1..pc2", "bi1..bi2"]),
    }
    for name, (x, y, w, h, fields) in entities.items():
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                     boxstyle="round,pad=0.02,rounding_size=0.05",
                                     facecolor="#fff", edgecolor=UPSA_NAVY,
                                     linewidth=1.4))
        # Header band
        ax.add_patch(FancyBboxPatch((x, y + h - 0.3), w, 0.3,
                                     boxstyle="square,pad=0",
                                     facecolor=UPSA_NAVY, edgecolor=UPSA_NAVY))
        ax.text(x + w / 2, y + h - 0.15, name,
                ha="center", va="center", fontsize=9.5,
                weight="bold", color="white")
        for i, f in enumerate(fields):
            ax.text(x + 0.12, y + h - 0.5 - i * 0.18, f,
                    fontsize=7.5, color=TEXT_DARK)

    # Relationships (line + label)
    def rel(x1, y1, x2, y2, label):
        ax.plot([x1, x2], [y1, y2], color="#666", lw=0.9)
        ax.text((x1 + x2) / 2, (y1 + y2) / 2, label,
                fontsize=7, color="#444", style="italic",
                ha="center", va="center", backgroundcolor="white")

    # User-Student (1..1)
    rel(3.5, 7.6, 4.5, 7.6, "1—1")
    # Student-Programme (N..1)
    rel(7.3, 7.8, 12.0, 7.8, "N—1")
    # User-Lecturer (1..1)
    rel(3.5, 8.4, 8.3, 8.4, "1—1")
    # Lecturer-Course (1..N)
    rel(9.7, 7.4, 9.7, 6.4, "1—N")
    # Course-ClassSession (1..N)
    rel(8.3, 5.6, 7.3, 5.6, "1—N")
    # ClassSession-AttendanceRecord (1..N)
    rel(4.5, 5.6, 3.8, 5.6, "1—N")
    # Student-AttendanceRecord (1..N)
    rel(4.5, 7.4, 2.4, 6.4, "1—N")
    # HikDevice-ClassSession (1..N)
    rel(2.4, 3.6, 4.5, 5.0, "1—N")
    # HikDevice-EventLog (1..N)
    rel(3.8, 2.8, 4.5, 2.8, "1—N")
    # Student-EnrollmentLog (1..N)
    rel(5.9, 7.4, 8.3, 3.6, "1—N")

    plt.savefig(OUT / "04_er_diagram.png",
                bbox_inches="tight", dpi=200, facecolor="white")
    plt.close()
    print("  ✓ 04_er_diagram.png")


# --------------------------------------------------------------------- 5. DEPLOYMENT / NETWORK
def diagram_deployment():
    fig, ax = setup_canvas(13, 8.5,
                           "Figure 3.5 — Deployment & Network Topology")

    # Wi-Fi cloud
    cloud = mpatches.Ellipse((6.5, 6.5), 4.0, 1.6,
                              facecolor="#eaf2fb", edgecolor=UPSA_NAVY,
                              linewidth=1.4)
    ax.add_patch(cloud)
    ax.text(6.5, 6.5, "UPSA Campus Wi-Fi (2.4 GHz)",
            ha="center", va="center", fontsize=11,
            weight="bold", color=UPSA_NAVY)

    # Devices
    box(ax, 1.0, 4.0, 3.0, 1.4,
        "Hikvision MinMoe\nDS-K1T323MBFWX-E1\n(192.168.x.y)",
        fill="#fff8e1", edge=UPSA_GOLD, bold=True)
    box(ax, 9.0, 4.0, 3.0, 1.4,
        "Application Server\nFlask + SQLite\n(192.168.x.z:5000)",
        fill="#fff", edge=UPSA_NAVY, bold=True)

    # Wi-Fi connections
    arrow(ax, 2.5, 5.4, 5.0, 6.2, lw=1.6, color=UPSA_NAVY,
          label="Wi-Fi")
    arrow(ax, 10.5, 5.4, 8.0, 6.2, lw=1.6, color=UPSA_NAVY,
          label="Wi-Fi")

    # Direct ISAPI line (logical)
    ax.annotate("", xy=(8.9, 4.7), xytext=(4.1, 4.7),
                arrowprops=dict(arrowstyle="<->", color=ACCENT,
                                lw=1.5, linestyle="--"))
    ax.text(6.5, 4.9, "Hikvision ISAPI (HTTP Digest, JSON)",
            ha="center", fontsize=9, color=ACCENT, style="italic")

    # End-user devices
    box(ax, 1.0, 1.4, 2.4, 1.0, "Lecturer Phone\n(browser)",
        fill="#fff", edge="#666")
    box(ax, 4.0, 1.4, 2.4, 1.0, "Admin Laptop\n(browser)",
        fill="#fff", edge="#666")
    box(ax, 7.0, 1.4, 2.4, 1.0, "Student Phone\n(browser)",
        fill="#fff", edge="#666")
    box(ax, 10.0, 1.4, 2.4, 1.0, "ICT Helpdesk\n(super admin)",
        fill="#fff", edge="#666")

    for cx in [2.2, 5.2, 8.2, 11.2]:
        arrow(ax, cx, 2.4, cx, 3.9, lw=1.0, color="#888")
        ax.text(cx + 0.05, 3.1, "HTTP", fontsize=7,
                color="#666")

    plt.savefig(OUT / "05_deployment.png",
                bbox_inches="tight", dpi=200, facecolor="white")
    plt.close()
    print("  ✓ 05_deployment.png")


# --------------------------------------------------------------------- main
if __name__ == "__main__":
    print(f"Generating diagrams to {OUT} ...")
    diagram_architecture()
    diagram_use_case()
    diagram_sequence()
    diagram_er()
    diagram_deployment()
    print("Done.")
