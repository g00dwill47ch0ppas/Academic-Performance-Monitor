import numpy as np
from flask import Blueprint, redirect, render_template, request, url_for

from backend.algorithms.nlp_weights import optimise_weights
from backend.data.store import data_store
from backend.models.student import Module
from backend.routes.cohort_helpers import weight_range_summary

cohort_bp = Blueprint("cohort", __name__)


def active_module_or_redirect() -> tuple[Module | None, object | None]:
    module = data_store.active_module
    if module is None:
        return None, redirect(url_for("modules.list_modules"))
    return module, None


def _parse_weight_ranges(
    module: Module, form: dict | None = None
) -> tuple[dict[str, float], dict[str, float]]:
    """Return ({name: min_weight_fraction}, {name: max_weight_fraction}) from form or defaults.

    Reads per-assessment minimum and maximum weights as percentages (0-100).
    Missing entries fall back to 0 (min) and 1 (max) so the optimizer is only
    constrained when the lecturer actually types a value.
    """
    mins: dict[str, float] = {}
    maxs: dict[str, float] = {}
    if form is None:
        form = {}
    for a in module.assessments:
        raw_min = (form.get(f"min_{a.name}") or "0").strip()
        raw_max = (form.get(f"max_{a.name}") or "100").strip()
        try:
            pct_min = float(raw_min)
        except ValueError:
            pct_min = 0.0
        try:
            pct_max = float(raw_max)
        except ValueError:
            pct_max = 100.0
        mins[a.name] = max(0.0, min(1.0, pct_min / 100.0))
        maxs[a.name] = max(0.0, min(1.0, pct_max / 100.0))
    return mins, maxs


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
                lower_bounds_map, upper_bounds_map = _parse_weight_ranges(module, request.form)
                for name, mx in upper_bounds_map.items():
                    if mx < lower_bounds_map.get(name, 0.0) - 1e-9:
                        flash(f"Max weight for '{name}' is below its min weight — fix the range.", "error")
                        break
                else:
                    lower_bounds = np.array([lower_bounds_map[a.name] for a in module.assessments])
                    upper_bounds = np.array([upper_bounds_map[a.name] for a in module.assessments])
                    optimal_weights = optimise_weights(
                        mark_matrix,
                        target,
                        current_weights,
                        lower_bounds=lower_bounds,
                        upper_bounds=upper_bounds,
                    )
                    result_rows = [
                        {
                            "assessment": name,
                            "current_weight": round(float(cw) * 100, 1),
                            "proposed_weight": round(float(ow) * 100, 1),
                            "min_weight_pct": round(float(lower_bounds_map.get(a.name, 0.0) * 100), 1),
                            "max_weight_pct": round(float(upper_bounds_map.get(a.name, 100.0) * 100), 1),
                        }
                        for name, cw, ow in zip(assessment_names, current_weights, optimal_weights)
                    ]
            except ValueError as e:
                error = str(e)

    if mark_matrix.shape[0] and mark_matrix.shape[1]:
        current_class_avg = round(float((mark_matrix @ current_weights).mean()), 1)
    else:
        current_class_avg = 0.0

    weight_ranges = weight_range_summary(module) if module.assessments else {}

    return render_template(
        "cohort_planning.html",
        module=module,
        target=target,
        result_rows=result_rows,
        error=error,
        current_class_avg=current_class_avg,
        weight_ranges=weight_ranges,
    )
