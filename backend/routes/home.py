from flask import Blueprint, flash, redirect, render_template, request, url_for

from backend.algorithms.lp_bounds import compute_pmark_bounds, is_at_risk
from backend.data.loader import PIIValidationError
from backend.data.store import data_store
from backend.models.student import Module

home_bp = Blueprint("home", __name__)


def active_module_or_redirect() -> tuple[Module | None, object | None]:
    module = data_store.active_module
    if module is None:
        return None, redirect(url_for("modules.list_modules"))
    return module, None


def module_rows(module: Module) -> list[dict]:
    """One summary row per student: p-mark bounds and at-risk flag (best case)."""
    threshold = module.config.pass_threshold
    rows = []
    for student in module.students:
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
    """Overview — headline statistics for the active module."""
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    rows = module_rows(module)
    class_average = round(sum(r["current_pmark"] for r in rows) / len(rows), 1) if rows else 0
    at_risk_count = sum(1 for r in rows if r["at_risk"])

    return render_template(
        "overview.html",
        module=module,
        class_average=class_average,
        at_risk_count=at_risk_count,
        class_size=len(rows),
    )


@home_bp.route("/at-risk")
def at_risk():
    """Students whose best-case p-mark cannot clear the module threshold."""
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    rows = module_rows(module)
    at_risk_rows = [r for r in rows if r["at_risk"]]

    return render_template(
        "at_risk.html",
        module=module,
        at_risk_rows=at_risk_rows,
        threshold=module.config.pass_threshold,
    )


@home_bp.route("/students")
def students():
    """Full cohort listing for the active module, with management actions."""
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    return render_template("students.html", module=module, rows=module_rows(module))


@home_bp.route("/settings")
def settings():
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    return render_template(
        "settings.html",
        module=module,
        threshold=module.config.pass_threshold,
        student_count=len(module.students),
        assessment_count=len(module.assessments),
    )


@home_bp.route("/threshold", methods=["POST"])
def update_threshold():
    module = data_store.active_module
    if module is None:
        return redirect(url_for("modules.list_modules"))
    try:
        module.config.pass_threshold = float(request.form["threshold"])
    except (KeyError, ValueError):
        flash("Invalid threshold value.", "error")
    return redirect(url_for("home.settings"))


@home_bp.route("/upload", methods=["POST"])
def upload():
    module = data_store.active_module
    if module is None:
        return redirect(url_for("modules.list_modules"))

    file = request.files.get("data_file")
    if not file or file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("home.settings"))

    try:
        data_store.replace_module_from_file(module, file, file.filename)
    except PIIValidationError as e:
        flash(str(e), "error")
    except ValueError as e:
        flash(f"Could not load file: {e}", "error")
    else:
        flash(
            f"Replaced module data with {len(module.students)} students and "
            f"{len(module.assessments)} assessments from {file.filename}.",
            "success",
        )
    return redirect(url_for("home.settings"))
