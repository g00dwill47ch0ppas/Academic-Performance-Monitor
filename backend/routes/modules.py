"""
Module management: create/rename/delete/switch modules, import modules from
CSV/XLSX, and edit the assessment plan (names + weights) of the active module.
"""

from io import BytesIO, StringIO

import pandas as pd
from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for

from backend.algorithms.lp_bounds import compute_pmark_bounds, is_at_risk
from backend.data.loader import PIIValidationError
from backend.data.store import DataStore, data_store
from backend.models.student import Module

module_bp = Blueprint("modules", __name__)


def active_module_or_redirect() -> tuple[Module | None, object | None]:
    module = data_store.active_module
    if module is None:
        return None, redirect(url_for("modules.list_modules"))
    return module, None


def parse_weight_percent(raw: str) -> float:
    """Parse a user-entered weight as a percentage and return a fraction (0, 1]."""
    try:
        percent = float(raw)
    except (TypeError, ValueError):
        raise ValueError("Weight must be a number (percentage).") from None
    if not 0 < percent <= 100:
        raise ValueError("Weight must be between 0% and 100%.")
    return percent / 100


# --------------------------------------------------------------------------- #
# Module lifecycle
# --------------------------------------------------------------------------- #
@module_bp.route("/modules")
def list_modules():
    modules = data_store.module_list()
    active = data_store.active_module
    return render_template("modules.html", modules=modules, active=active)


@module_bp.route("/modules/create", methods=["POST"])
def create_module():
    code = request.form.get("module_code", "").strip()
    name = request.form.get("module_name", "").strip()
    try:
        data_store.create_module(code, name)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("modules.list_modules"))
    flash(f"Module '{data_store.active_module.label}' created.", "success")
    return redirect(url_for("home.home"))


@module_bp.route("/modules/import", methods=["POST"])
def import_module():
    code = request.form.get("module_code", "").strip()
    name = request.form.get("module_name", "").strip()
    file = request.files.get("data_file")
    if not code:
        flash("Module code cannot be empty.", "error")
        return redirect(url_for("modules.list_modules"))
    if not file or file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("modules.list_modules"))
    try:
        module = data_store.create_module_from_file(code, name, file, file.filename)
    except PIIValidationError as e:
        flash(str(e), "error")
    except ValueError as e:
        flash(str(e), "error")
    else:
        flash(
            f"Imported {len(module.students)} students and {len(module.assessments)} "
            f"assessments into '{module.label}'.",
            "success",
        )
        return redirect(url_for("home.home"))
    return redirect(url_for("modules.list_modules"))


@module_bp.route("/modules/<code>/edit", methods=["GET", "POST"])
def edit_module(code: str):
    module = data_store.modules.get(code)
    if module is None:
        flash("Module not found.", "error")
        return redirect(url_for("modules.list_modules"))

    if request.method == "POST":
        new_code = request.form.get("module_code", "").strip()
        new_name = request.form.get("module_name", "").strip()
        try:
            data_store.rename_module(code, new_code, new_name)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("modules.edit_module", code=code))
        flash("Module updated.", "success")
        return redirect(url_for("modules.list_modules"))

    return render_template(
        "edit_module.html",
        module=module,
        student_count=len(module.students),
        assessment_count=len(module.assessments),
    )


@module_bp.route("/modules/<code>/delete", methods=["POST"])
def delete_module(code: str):
    deleted = data_store.modules.get(code)
    if deleted is None:
        flash("Module not found.", "error")
        return redirect(url_for("modules.list_modules"))

    label = deleted.label
    data_store.delete_module(code)
    if data_store.active_module is None:
        flash(f"Deleted '{label}'. Create a module to get started.", "success")
        return redirect(url_for("modules.list_modules"))
    flash(
        f"Deleted '{label}'. Now viewing '{data_store.active_module.label}'.",
        "success",
    )
    return redirect(url_for("home.home"))


@module_bp.route("/modules/<code>/activate")
def activate(code: str):
    """Switch the lecturer to this module (single-user prototype, so this is a
    straightforward store-side selection rather than a per-user preference)."""
    if not data_store.activate(code):
        flash("Module not found.", "error")
        return redirect(url_for("modules.list_modules"))
    return redirect(url_for("home.home"))


@module_bp.route("/modules/<code>/export")
def export_module(code: str):
    """Download the module's data as CSV in the same long format the importer
    expects (student_code, assessment_name, weight, mark, completed) so exports
    can be re-imported unchanged."""
    module = data_store.modules.get(code)
    if module is None:
        flash("Module not found.", "error")
        return redirect(url_for("modules.list_modules"))

    df: pd.DataFrame = DataStore.module_to_dataframe(module)
    buffer = StringIO()
    df.to_csv(buffer, index=False)
    payload = BytesIO(buffer.getvalue().encode("utf-8"))
    return send_file(
        payload,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"{code}_data.csv",
    )


@module_bp.route("/modules/<code>/summary-export")
def summary_export(code: str):
    """Download a per-student summary (p-mark, min/max bounds, at-risk flag)
    computed with the module's current pass threshold."""
    module = data_store.modules.get(code)
    if module is None:
        flash("Module not found.", "error")
        return redirect(url_for("modules.list_modules"))

    threshold = module.config.pass_threshold
    records = []
    for student in module.students:
        min_pm, max_pm = compute_pmark_bounds(student.assessments)
        records.append(
            {
                "student_code": student.student_code,
                "current_pmark": round(student.p_mark_current, 2),
                "min_pmark": min_pm,
                "max_pmark": max_pm,
                "at_risk": is_at_risk(max_pm, threshold),
            }
        )
    df = pd.DataFrame(
        records,
        columns=["student_code", "current_pmark", "min_pmark", "max_pmark", "at_risk"],
    )
    buffer = StringIO()
    df.to_csv(buffer, index=False)
    payload = BytesIO(buffer.getvalue().encode("utf-8"))
    return send_file(
        payload,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"{code}_summary.csv",
    )


# --------------------------------------------------------------------------- #
# Assessment plan for the active module
# --------------------------------------------------------------------------- #
@module_bp.route("/plan")
def plan():
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    completed_counts = {}
    for plan_entry in module.assessments:
        completed_counts[plan_entry.name] = sum(
            1
            for s in module.students
            if (a := module.student_assessment(s, plan_entry.name)) is not None
            and a.completed
        )
    return render_template(
        "plan.html",
        module=module,
        completed_counts=completed_counts,
        total_weights=round(sum(a.weight for a in module.assessments) * 100, 1),
    )


@module_bp.route("/plan/add", methods=["POST"])
def add_assessment():
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    name = request.form.get("assessment_name", "").strip()
    try:
        weight = parse_weight_percent(request.form.get("weight", ""))
        if "/" in name:
            raise ValueError("Assessment names cannot contain a '/'.")
        data_store.add_assessment(module, name, weight)
    except ValueError as e:
        flash(str(e), "error")
    else:
        flash(f"Assessment '{name}' added to the plan.", "success")
    return redirect(url_for("modules.plan"))


@module_bp.route("/plan/<path:name>/update", methods=["POST"])
def update_assessment(name: str):
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    try:
        weight = parse_weight_percent(request.form.get("weight", ""))
        data_store.update_assessment(module, name, weight)
    except ValueError as e:
        flash(str(e), "error")
    else:
        flash(f"Weight for '{name}' updated.", "success")
    return redirect(url_for("modules.plan"))


@module_bp.route("/plan/<path:name>/delete", methods=["POST"])
def delete_assessment(name: str):
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    data_store.delete_assessment(module, name)
    flash(f"Assessment '{name}' removed from the plan and all students.", "success")
    return redirect(url_for("modules.plan"))
