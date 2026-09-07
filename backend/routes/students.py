"""Per-student views for the active module: detail, and add/edit/remove."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from backend.algorithms.lp_bounds import compute_pmark_bounds
from backend.algorithms.participation_plan import generate_participation_plan
from backend.data.store import data_store
from backend.models.student import Module

students_bp = Blueprint("students", __name__)


def active_module_or_redirect() -> tuple[Module | None, object | None]:
    module = data_store.active_module
    if module is None:
        return None, redirect(url_for("modules.list_modules"))
    return module, None


def _parse_marks(module: Module, form) -> list[float | None]:
    """Read mark_{i} fields aligned with the module plan. Blank = not completed.

    A mark must be a number in [0, 100] when provided.
    """
    marks: list[float | None] = []
    for i, plan in enumerate(module.assessments):
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
    for i in range(len(module.assessments)):
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


@students_bp.route("/student/<student_code>")
def student_detail(student_code: str):
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    student = module.student(student_code)
    if student is None:
        abort(404)

    min_pm, max_pm = compute_pmark_bounds(student.assessments)

    target_pct = int(request.args.get("target_pct", 10))
    scenarios = generate_participation_plan(
        student.assessments, student.p_mark_current, target_pct
    )

    return render_template(
        "student_detail.html",
        module=module,
        student=student,
        min_pmark=min_pm,
        max_pmark=max_pm,
        target_pct=target_pct,
        scenarios=scenarios,
        target_pmark=round(student.p_mark_current * (1 + target_pct / 100), 1),
        all_codes=sorted(s.student_code for s in module.students),
    )
