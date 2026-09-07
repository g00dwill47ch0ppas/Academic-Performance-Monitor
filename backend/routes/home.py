from flask import Blueprint, flash, redirect, render_template, request, url_for

from backend.algorithms.lp_bounds import compute_pmark_bounds, is_at_risk
from backend.data.loader import PIIValidationError
from backend.data.store import data_store

home_bp = Blueprint("home", __name__)


def _cohort_rows():
    """Build one row per student with p-mark bounds and at-risk flag."""
    threshold = data_store.config.pass_threshold
    rows = []
    for student in data_store.all_students():
        min_pm, max_pm = compute_pmark_bounds(student.assessments)
        rows.append(
            {
                "student_code": student.student_code,
                "current_pmark": round(student.p_mark_current, 1),
                "min_pmark": min_pm,
                "max_pmark": max_pm,
                "at_risk": is_at_risk(max_pm, threshold),
            }
        )
    return rows


@home_bp.route("/")
def home():
    """Overview — headline class statistics."""
    rows = _cohort_rows()
    class_average = round(sum(r["current_pmark"] for r in rows) / len(rows), 1) if rows else 0
    at_risk_count = sum(1 for r in rows if r["at_risk"])

    return render_template(
        "overview.html",
        class_average=class_average,
        at_risk_count=at_risk_count,
        class_size=len(rows),
        threshold=data_store.config.pass_threshold,
    )


@home_bp.route("/at-risk")
def at_risk():
    """Students whose best-case p-mark cannot clear the pass threshold."""
    rows = _cohort_rows()
    at_risk_rows = [r for r in rows if r["at_risk"]]

    return render_template(
        "at_risk.html",
        at_risk_rows=at_risk_rows,
        threshold=data_store.config.pass_threshold,
    )


@home_bp.route("/students")
def students():
    """Full cohort listing with per-student bounds."""
    return render_template("students.html", rows=_cohort_rows())


@home_bp.route("/settings")
def settings():
    """Threshold and data upload settings."""
    return render_template("settings.html", threshold=data_store.config.pass_threshold)


@home_bp.route("/threshold", methods=["POST"])
def update_threshold():
    try:
        data_store.config.pass_threshold = float(request.form["threshold"])
    except (KeyError, ValueError):
        flash("Invalid threshold value.", "error")
    return redirect(url_for("home.settings"))


@home_bp.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("data_file")
    if not file or file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("home.settings"))

    try:
        data_store.load_from_upload(file)
        flash(
            f"Loaded {len(data_store.student_codes())} students from {file.filename}.",
            "success",
        )
    except PIIValidationError as e:
        flash(str(e), "error")
    except ValueError as e:
        flash(f"Could not load file: {e}", "error")

    return redirect(url_for("home.settings"))
