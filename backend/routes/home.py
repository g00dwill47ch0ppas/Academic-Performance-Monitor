from flask import Blueprint, flash, redirect, render_template, request, url_for

from backend.algorithms.lp_bounds import is_at_risk
from backend.data.loader import PIIValidationError
from backend.data.store import data_store
from backend.models.student import Module
from backend.services.participation import analyse

home_bp = Blueprint("home", __name__)


def active_module_or_redirect() -> tuple[Module | None, object | None]:
    module = data_store.active_module
    if module is None:
        return None, redirect(url_for("modules.list_modules"))
    return module, None


def module_rows(module: Module) -> list[dict]:
    """One summary row per student: participation, region bounds and risk flag.

    Every figure comes from the participation rule engine, so the drop rule is
    applied identically here and on the student detail page.
    """
    threshold = module.config.pass_threshold
    rows = []
    for student in module.students:
        participation = analyse(student.assessments)
        rows.append(
            {
                "student_code": student.student_code,
                "accrued": participation.accrued,
                "standing": participation.standing,
                "min_pmark": participation.min_final,
                "max_pmark": participation.max_final,
                "dropped_count": len(participation.dropped_items),
                "remaining_slots": participation.remaining_slots,
                "at_risk": is_at_risk(participation.max_final, threshold),
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
    class_average = sum(r["accrued"] for r in rows) / len(rows) if rows else 0.0
    at_risk_count = sum(1 for r in rows if r["at_risk"])
    dropped_count = sum(r["dropped_count"] for r in rows)

    return render_template(
        "overview.html",
        module=module,
        class_average=class_average,
        at_risk_count=at_risk_count,
        class_size=len(rows),
        dropped_count=dropped_count,
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
        item_count=len(module.plan_items()),
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
