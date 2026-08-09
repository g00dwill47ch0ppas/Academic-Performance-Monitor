from flask import Blueprint, flash, redirect, render_template, request, url_for

from backend.algorithms.lp_bounds import compute_pmark_bounds, is_at_risk
from backend.data.loader import PIIValidationError
from backend.data.store import data_store

home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def home():
    threshold = data_store.config.pass_threshold

    students = data_store.all_students()
    rows = []
    for student in students:
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

    class_average = round(sum(r["current_pmark"] for r in rows) / len(rows), 1) if rows else 0
    at_risk_rows = [r for r in rows if r["at_risk"]]

    return render_template(
        "index.html",
        rows=rows,
        at_risk_rows=at_risk_rows,
        class_average=class_average,
        class_size=len(rows),
        threshold=threshold,
    )


@home_bp.route("/threshold", methods=["POST"])
def update_threshold():
    try:
        data_store.config.pass_threshold = float(request.form["threshold"])
    except (KeyError, ValueError):
        flash("Invalid threshold value.", "error")
    return redirect(url_for("home.home"))


@home_bp.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("data_file")
    if not file or file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("home.home"))

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

    return redirect(url_for("home.home"))
