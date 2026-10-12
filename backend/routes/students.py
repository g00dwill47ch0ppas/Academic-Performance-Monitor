"""Per-student views for the active module: detail, and add/edit/remove.

Also supports bulk mark import from a CSV (one assessment per file) and bulk
student + mark import from a CSV."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from backend.algorithms.participation_plan import build_projection, feasible_region
from backend.data.store import data_store
from backend.models.student import Module
from backend.routes.modules_helpers import parse_mark_import_csv, parse_student_import_csv
from backend.services.participation import analyse

students_bp = Blueprint("students", __name__)


def active_module_or_redirect() -> tuple[Module | None, object | None]:
    module = data_store.active_module
    if module is None:
        return None, redirect(url_for("modules.list_modules"))
    return module, None


def _parse_marks(module: Module, form) -> list[float | None]:
    """Read mark_{i} fields aligned with the module's plan ITEMS.

    Blank = not written yet (NOT zero). A mark must be a number in [0, 100] when
    provided.
    """
    marks: list[float | None] = []
    for i, plan in enumerate(module.plan_items()):
        raw = form.get(f"mark_{i}", "").strip()
        if raw == "":
            marks.append(None)
            continue
        try:
            value = float(raw)
        except ValueError:
            raise ValueError(f"Mark for '{plan.name}' must be a number.") from None
        if not 0 <= value <= 100:
            raise ValueError(f"Mark for '{plan.name}' must be between 0 and 100.")
        marks.append(value)
    return marks


def _mark_raw_list(module: Module, form, student=None) -> list[str]:
    """Rebuild the form's mark inputs (for error re-render or prefill)."""
    raws: list[str] = []
    for i in range(len(module.plan_items())):
        if form is not None and f"mark_{i}" in form:
            raws.append(form.get(f"mark_{i}", ""))
        elif student is not None and i < len(student.assessments):
            a = student.assessments[i]
            raws.append("" if a.mark is None else str(a.mark))
        else:
            raws.append("")
    return raws


@students_bp.route("/students/new", methods=["GET", "POST"])
def add_student():
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    if request.method == "POST":
        # Single-student form path.
        if request.form.get("source") == "single":
            code = request.form.get("student_code", "").strip()
            try:
                marks = _parse_marks(module, request.form)
                data_store.add_student(module, code, marks)
            except ValueError as e:
                flash(str(e), "error")
                return render_template(
                    "student_form.html",
                    module=module,
                    student=None,
                    marks_raw=_mark_raw_list(module, request.form),
                    form_code=code,
                    form_action=url_for("students.add_student"),
                )
            flash(f"Student '{code}' added.", "success")
            return redirect(url_for("home.students"))

        # Bulk CSV import path.
        file = request.files.get("import_file")
        if not file or file.filename == "":
            flash("Select a CSV file to import.", "error")
            return redirect(url_for("students.add_student"))
        rows, error = parse_student_import_csv(module, file, file.filename)
        if error:
            flash(error, "error")
            return redirect(url_for("students.add_student"))
        if not rows:
            flash("No valid rows in the file.", "error")
            return redirect(url_for("students.add_student"))

        added = 0
        for entry in rows:
            try:
                data_store.add_student(module, entry["code"], entry["marks"])
                added += 1
            except ValueError as e:
                flash(str(e), "error")
        flash(f"Imported {added} student(s) from file.", "success")
        return redirect(url_for("home.students"))

    return render_template(
        "student_form.html",
        module=module,
        student=None,
        marks_raw=_mark_raw_list(module, None),
        form_code="",
        form_action=url_for("students.add_student"),
    )


@students_bp.route("/student/<student_code>/edit", methods=["GET", "POST"])
def edit_student(student_code: str):
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    student = module.student(student_code)
    if student is None:
        abort(404)

    if request.method == "POST":
        new_code = request.form.get("student_code", "").strip()
        try:
            marks = _parse_marks(module, request.form)
            data_store.update_student(module, student_code, new_code, marks)
        except ValueError as e:
            flash(str(e), "error")
            return render_template(
                "student_form.html",
                module=module,
                student=student,
                marks_raw=_mark_raw_list(module, request.form),
                form_code=new_code,
                form_action=url_for("students.edit_student", student_code=student_code),
            )
        flash(f"Student '{new_code}' updated.", "success")
        return redirect(url_for("students.student_detail", student_code=new_code))

    return render_template(
        "student_form.html",
        module=module,
        student=student,
        marks_raw=_mark_raw_list(module, None, student),
        form_code=student.student_code,
        form_action=url_for("students.edit_student", student_code=student_code),
    )


@students_bp.route("/student/<student_code>/delete", methods=["POST"])
def delete_student(student_code: str):
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    if module.student(student_code) is None:
        abort(404)
    data_store.delete_student(module, student_code)
    flash(f"Student '{student_code}' removed.", "success")
    return redirect(url_for("home.students"))


@students_bp.route("/students/import", methods=["GET", "POST"])
def student_csv_import():
    """Bulk import students + marks from a CSV (one mark column per assessment)."""
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    if request.method == "POST":
        file = request.files.get("import_file")
        if not file or file.filename == "":
            flash("Select a CSV file to import.", "error")
            return redirect(url_for("students.student_csv_import"))
        rows, error = parse_student_import_csv(module, file, file.filename)
        if error:
            flash(error, "error")
            return redirect(url_for("students.student_csv_import"))
        if not rows:
            flash("No valid rows in the file.", "error")
            return redirect(url_for("students.student_csv_import"))

        added = 0
        for entry in rows:
            try:
                data_store.add_student(module, entry["code"], entry["marks"])
                added += 1
            except ValueError as e:
                flash(str(e), "error")
        flash(f"Imported {added} student(s) from file.", "success")
        return redirect(url_for("home.students"))

    return render_template(
        "student_csv_import.html",
        module=module,
        plan_items=module.plan_items(),
        plan_count=len(module.plan_items()),
    )


@students_bp.route("/marks/import", methods=["POST"])
def bulk_marks_import():
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    source = request.form.get("import_source", "")
    if source == "csv":
        file = request.files.get("import_file")
        if not file or file.filename == "":
            flash("Select a CSV file to import.", "error")
            return redirect(url_for("students.bulk_marks"))
        name, rows, error = parse_mark_import_csv(module, file, file.filename)
        if error:
            flash(error, "error")
            return redirect(url_for("students.bulk_marks"))
        if not rows:
            flash("No valid rows in the file.", "error")
            return redirect(url_for("students.bulk_marks"))

        marks: dict[str, float | None] = {code: mark for code, mark in rows}
        try:
            data_store.set_assessment_marks(module, name, marks)
        except ValueError as e:
            flash(str(e), "error")
        else:
            applied = sum(1 for m in marks.values() if m is not None)
            skipped = len(marks) - applied
            flash(
                f"Imported {applied} mark(s) for '{name}' across {len(marks)} student(s)"
                + (f"; {skipped} left blank" if skipped else ""),
                "success",
            )
        return redirect(url_for("students.bulk_marks", assessment=name))

    flash("Unknown import source.", "error")
    return redirect(url_for("students.bulk_marks"))


@students_bp.route("/marks", methods=["GET", "POST"])
def bulk_marks():
    """Bulk mark entry: pick one assessment and enter it for the whole class."""
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    plan_items = module.plan_items()
    names = [item.name for item in plan_items]
    if request.method == "POST":
        name = request.form.get("assessment", "")
        try:
            marks = {}
            for student in module.students:
                raw = request.form.get(f"mark_{student.student_code}", "").strip()
                if raw == "":
                    marks[student.student_code] = None
                    continue
                try:
                    value = float(raw)
                except ValueError:
                    raise ValueError(
                        f"Mark for {student.student_code} must be a number."
                    ) from None
                if not 0 <= value <= 100:
                    raise ValueError(
                        f"Mark for {student.student_code} must be between 0 and 100."
                    )
                marks[student.student_code] = value
            data_store.set_assessment_marks(module, name, marks)
        except ValueError as e:
            flash(str(e), "error")
            return render_template(
                "marks.html",
                module=module,
                items=plan_items,
                selected=name,
                raws=request.form,
                student_state=_participation_by_student(module),
            )
        flash(f"Marks for '{name}' saved for {len(module.students)} students.", "success")
        return redirect(url_for("students.bulk_marks", assessment=name))

    selected = request.args.get("assessment")
    if selected not in names:
        selected = names[0] if names else ""

    return render_template(
        "marks.html",
        module=module,
        items=plan_items,
        selected=selected,
        raws=None,
        student_state=_participation_by_student(module),
    )


def _participation_by_student(module: Module) -> dict[str, dict]:
    """Per-student participation summary for the mark-entry grid.

    Shows the lecturer which of a student's marks are counted, which are dropped
    and what the mark currently stands at, all from the same rule engine.
    """
    state: dict[str, dict] = {}
    for student in module.students:
        participation = analyse(student.assessments)
        state[student.student_code] = {
            "accrued": participation.accrued,
            "standing": participation.standing,
            "counted": {r.name for r in participation.counted_items},
            "dropped": {r.name for r in participation.dropped_items},
        }
    return state


@students_bp.route("/student/<student_code>")
def student_detail(student_code: str):
    """One student: participation so far, the feasible region, and a target plan.

    The lecturer picks an absolute target final participation mark, which must sit
    inside the student's feasible region. The UI restricts the slider to that
    region and this route re-validates whatever arrives, because the browser is
    only a convenience — the server is the arbiter.
    """
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    student = module.student(student_code)
    if student is None:
        abort(404)

    threshold = module.config.pass_threshold
    participation = analyse(student.assessments)
    region = feasible_region(student.assessments, threshold)

    # Default target: the pass threshold when it sits inside the region (the
    # usual goal), otherwise the middle of the region so the first render always
    # shows a meaningful plan. The threshold stays marked on the bar either way.
    if region.minimum <= threshold <= region.maximum:
        target = threshold
    else:
        target = (region.minimum + region.maximum) / 2
    target_error = None
    raw_target = (request.args.get("target") or "").strip()
    if raw_target:
        try:
            requested = float(raw_target)
        except ValueError:
            target_error = "Enter the target as a number, e.g. 62.5."
        else:
            if requested < region.minimum - 1e-9 or requested > region.maximum + 1e-9:
                target_error = (
                    f"Choose a target between {region.minimum:.2f}% and "
                    f"{region.maximum:.2f}% — that is this student's feasible region."
                )
                target = min(max(requested, region.minimum), region.maximum)
            else:
                target = requested

    projection = build_projection(student.assessments, target, threshold)

    return render_template(
        "student_detail.html",
        module=module,
        student=student,
        participation=participation,
        region=region,
        projection=projection,
        target=target,
        target_error=target_error,
        threshold=threshold,
        all_codes=sorted(s.student_code for s in module.students),
    )
