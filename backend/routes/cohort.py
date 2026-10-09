"""
Cohort planning — Algorithm 3 (Van der Merwe et al., 2018b) driven by lecturer
weight *ranges*.

The lecturer sets a range [min%, max%] for every assessment in the active module's
plan; those ranges are the constraints of the non-linear weight optimisation in
``backend.algorithms.nlp_weights``. This module is only responsible for

  * turning the submitted form into (target average, lower bounds, upper bounds),
  * validating the hard rules at the HTTP boundary (positive minimums, min <= max,
    ranges that can add up to 100%, numeric input),
  * and handing the solver's status back to the page so nothing fails silently.

Every rule is enforced twice — once in JavaScript for immediate feedback and once
here, because the JavaScript is only a convenience and the server is the arbiter.
"""

import numpy as np
from flask import Blueprint, flash, redirect, render_template, request, url_for

from backend.algorithms.nlp_weights import (
    MIN_WEIGHT_FRACTION,
    WeightRangeError,
    solve_weight_ranges,
    validate_weight_ranges,
)
from backend.data.store import data_store
from backend.models.student import Module

cohort_bp = Blueprint("cohort", __name__)

#: Smallest weight an assessment may carry, as a percentage (see nlp_weights).
MIN_WEIGHT_PCT = round(MIN_WEIGHT_FRACTION * 100, 1)

#: Default pre-fill: the current weight ± 10 percentage points.
DEFAULT_RANGE_SPREAD = 10.0


def active_module_or_redirect() -> tuple[Module | None, object | None]:
    module = data_store.active_module
    if module is None:
        return None, redirect(url_for("modules.list_modules"))
    return module, None


def _mark_matrix(module: Module) -> np.ndarray:
    """Mark matrix (students × plan assessments), 0 for not-yet-completed.

    # TODO: confirm against source paper — an assessment the class has not written
    # yet counts as 0 in the class average the objective compares against the
    # target, which pulls the reachable average down. The objective itself is
    # unchanged (Van der Merwe et al., 2018b); only the mark data could arguably be
    # projected instead. Flagged rather than silently changed.
    """
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


def _default_ranges(module: Module) -> dict[str, dict[str, float]]:
    """Pre-fills each assessment's range with ±10 points around its current weight.

    Clamped to the 1% floor and 100%, so the default form is always valid and
    never proposes a zero-weight assessment.
    """
    defaults: dict[str, dict[str, float]] = {}
    for a in module.assessments:
        current = round(a.weight * 100, 1)
        low = max(MIN_WEIGHT_PCT, round(current - DEFAULT_RANGE_SPREAD, 1))
        high = min(100.0, round(current + DEFAULT_RANGE_SPREAD, 1))
        defaults[a.name] = {"min": low, "max": max(low, high), "current": current}
    return defaults


def _read_target(form, stored: float) -> tuple[float, str | None]:
    """Target class average from the form; missing/blank keeps the stored value.

    The target used to be read with ``form["target_average"]`` while the slider
    lived outside the submitted form, which made every submission fail with
    "Invalid target average". It now tolerates an absent field and only reports an
    error when a value was actually typed and is unusable.
    """
    raw = (form.get("target_average") or "").strip()
    if raw == "":
        return stored, None
    try:
        target = float(raw)
    except ValueError:
        return stored, "Enter the target class average as a number, e.g. 62."
    if not 0.0 <= target <= 100.0:
        return stored, "The target class average must be between 0% and 100%."
    return target, None


def _read_ranges(
    module: Module, form, defaults: dict[str, dict[str, float]]
) -> tuple[dict[str, float], dict[str, float], str | None]:
    """Per-assessment min/max percentages from the form, falling back to defaults.

    Blank fields revert to the pre-filled default (the current weight ±10) rather
    than to 0/100, so an untouched form always solves. Non-numeric input is
    reported instead of being silently coerced.
    """
    mins: dict[str, float] = {}
    maxs: dict[str, float] = {}
    for a in module.assessments:
        default = defaults[a.name]
        for field, store, label in (
            ("min", mins, "Minimum"),
            ("max", maxs, "Maximum"),
        ):
            raw = (form.get(f"{field}_{a.name}") or "").strip()
            if raw == "":
                store[a.name] = float(default[field])
                continue
            try:
                store[a.name] = float(raw)
            except ValueError:
                return (
                    mins,
                    maxs,
                    f"{label} weight for '{a.name}' must be a number (percentage).",
                )
    return mins, maxs, None


@cohort_bp.route("/cohort", methods=["GET", "POST"])
def cohort_planning():
    module, response = active_module_or_redirect()
    if response is not None:
        return response

    assessment_names = [a.name for a in module.assessments]
    current_weights = np.array([a.weight for a in module.assessments])
    mark_matrix = _mark_matrix(module)

    target = module.config.target_class_average
    defaults = _default_ranges(module)
    entered = {name: dict(values) for name, values in defaults.items()}

    solution = None
    result_rows = None
    error = None
    submitted = False

    if request.method == "POST":
        submitted = True
        target, error = _read_target(request.form, target)
        mins, maxs, range_error = _read_ranges(module, request.form, defaults)
        if error is None and range_error is not None:
            error = range_error

        # Echo back what the lecturer typed, so a validation error does not wipe
        # their input and the page looks exactly as they left it.
        for name in defaults:
            entered[name]["min"] = round(mins.get(name, defaults[name]["min"]), 1)
            entered[name]["max"] = round(maxs.get(name, defaults[name]["max"]), 1)

        if error is None and not assessment_names:
            error = "This module has no assessments yet. Add an assessment plan first."
        elif error is None and mark_matrix.shape[0] == 0:
            error = "This module has no students yet. Add students first and their marks."
        elif error is None:
            try:
                lower_bounds = np.array([mins[a.name] / 100.0 for a in module.assessments])
                upper_bounds = np.array([maxs[a.name] / 100.0 for a in module.assessments])
                # Re-validate here so the exact same rules that the JS checks are
                # enforced server-side (and the floor is applied for display).
                validate_weight_ranges(lower_bounds, upper_bounds, assessment_names)
                effective_lower = np.maximum(lower_bounds, MIN_WEIGHT_FRACTION)
                solution = solve_weight_ranges(
                    mark_matrix,
                    target,
                    lower_bounds,
                    upper_bounds,
                    initial_weights=current_weights,
                    names=assessment_names,
                )
            except WeightRangeError as exc:
                error = str(exc)
            else:
                if solution.ok:
                    module.config.target_class_average = target
                    result_rows = [
                        {
                            "assessment": name,
                            "current_weight": round(float(cw) * 100, 1),
                            "proposed_weight": round(float(ow) * 100, 1),
                            "min_weight_pct": round(
                                float(effective_lower[i]) * 100, 1
                            ),
                            "user_min_pct": round(mins[name], 1),
                            "max_weight_pct": round(maxs[name], 1),
                            "floor_applied": mins[name] < MIN_WEIGHT_PCT,
                        }
                        for i, (name, cw, ow) in enumerate(
                            zip(assessment_names, current_weights, solution.weights)
                        )
                    ]
                    flash(
                        f"Optimised weights using {len(assessment_names)} assessment "
                        f"ranges (target {target:.1f}%).",
                        "success",
                    )
                # A non-optimal status keeps its message from the solver and is
                # rendered as a status banner below (never an empty table).

    if mark_matrix.shape[0] and mark_matrix.shape[1]:
        current_class_avg = round(float((mark_matrix @ current_weights).mean()), 1)
    else:
        current_class_avg = 0.0

    sum_min = round(sum(v["min"] for v in entered.values()), 1)
    sum_max = round(sum(v["max"] for v in entered.values()), 1)

    return render_template(
        "cohort_planning.html",
        module=module,
        target=target,
        ranges=entered,
        submitted=submitted,
        result_rows=result_rows,
        solution=solution,
        error=error,
        current_class_avg=current_class_avg,
        sum_min=sum_min,
        sum_max=sum_max,
        min_weight_pct=MIN_WEIGHT_PCT,
    )
