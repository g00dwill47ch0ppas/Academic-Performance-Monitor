import numpy as np
from flask import Blueprint, redirect, render_template, request, url_for

from backend.algorithms.nlp_weights import optimise_weights
from backend.data.store import data_store
from backend.models.student import Module

cohort_bp = Blueprint("cohort", __name__)


def active_module_or_redirect() -> tuple[Module | None, object | None]:
    module = data_store.active_module
    if module is None:
        return None, redirect(url_for("modules.list_modules"))
    return module, None


def _mark_matrix(module: Module) -> np.ndarray:
    """Mark matrix (students × plan assessments), 0 for not-yet-completed."""
    names = [a.name for a in module.assessments]
    rows = []
    for student in module.students:
        by_name = {a.name: a for a in student.assessments}
        row = []
        for name in names:
            entry = by_name.get(name)
            row.append(entry.mark if entry is not None and entry.completed else 0.0)
        rows.append(row)
    if not rows:
        return np.zeros((0, len(names)))
    return np.array(rows)


@cohort_bp.route("/cohort", methods=["GET", "POST"])
def cohort_planning():
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    assessment_names = [a.name for a in module.assessments]
    current_weights = np.array([a.weight for a in module.assessments])
    mark_matrix = _mark_matrix(module)

    target = module.config.target_class_average
    result_rows = None
    error = None

    if request.method == "POST":
        try:
            target = float(request.form["target_average"])
            module.config.target_class_average = target
        except (KeyError, ValueError):
            error = "Invalid target average."

        if error is None and len(assessment_names) == 0:
            error = "This module has no assessments yet. Add an assessment plan first."
        elif error is None and mark_matrix.shape[0] == 0:
            error = "This module has no students yet. Add students first."
        elif error is None:
            try:
                optimal_weights = optimise_weights(mark_matrix, target, current_weights)
                result_rows = [
                    {
                        "assessment": name,
                        "current_weight": round(float(cw) * 100, 1),
                        "proposed_weight": round(float(ow) * 100, 1),
                    }
                    for name, cw, ow in zip(assessment_names, current_weights, optimal_weights)
                ]
            except ValueError as e:
                error = str(e)

    if mark_matrix.shape[0] and mark_matrix.shape[1]:
        current_class_avg = round(float((mark_matrix @ current_weights).mean()), 1)
    else:
        current_class_avg = 0.0

    return render_template(
        "cohort_planning.html",
        module=module,
        target=target,
        result_rows=result_rows,
        error=error,
        current_class_avg=current_class_avg,
    )
