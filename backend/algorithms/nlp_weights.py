"""
Algorithm 3 — Non-Linear Programming weight optimisation.

Based on Van der Merwe et al. (2018b). Given a class's current per-assessment marks
and a lecturer-specified target class average, computes the assessment weight
combination that would achieve that target.

CONSTRAINTS (_the part the cohort-planning page drives_)
    The lecturer picks a range [min_i, max_i] per assessment. Those ranges become
    the constraints of the problem:

        sum(w_i)      = 1                      (weights add up to 100%)
        w_i          >= max(min_i, 1%)         (see "no zero weights" note)
        w_i          <= max_i
        sum(min_i)   <= 1 <= sum(max_i)        (feasibility, checked up front)

    Every assessment must keep a strictly positive weight, so the effective lower
    bound is never below ``MIN_WEIGHT_FRACTION`` (1%). Ranges that break those
    rules raise :class:`WeightRangeError` with a message that says which rule
    failed and by how much, and cannot be solved into a silent zero-weight plan.

NOTE ON TECH STACK: this project uses PuLP for Algorithm 1 to match the project's
chosen LP library, but PuLP solves linear/mixed-integer problems only — it cannot
express the non-linear objective this algorithm requires. Reformulating Algorithm 3
as a linear approximation would modify the mathematical model, which the research
proposal (§1.4.6) explicitly rules out ("adopted directly ... not modified").
scipy.optimize is therefore used for this one algorithm only.

# TODO: confirm against source paper —
#   1. Must weights sum to exactly 1 (enforced here as an equality constraint)?
#   2. The per-assessment minimum/maximum bounds enforced here come from the
#      lecturer's input on the cohort-planning page; confirm whether the paper
#      itself prescribes default bounds (e.g. no assessment below 5% or above 50%).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

#: Every assessment must carry weight, so no lower bound is allowed below this
#: fraction (1% of the final mark).
MIN_WEIGHT_FRACTION = 0.01

#: Tolerances used when verifying the returned solution against the constraints.
_SUM_TOLERANCE = 1e-4
_RANGE_TOLERANCE = 1e-4

#: A proposed average this close to the target counts as "on target".
_ON_TARGET_TOLERANCE = 0.05


class WeightRangeError(ValueError):
    """The lecturer's per-assessment weight ranges cannot be solved as given."""


@dataclass
class WeightSolution:
    """Outcome of one optimisation run, including a human-readable status."""

    status: str                      # "optimal" | "infeasible" | "failed"
    message: str                     # explanation shown in the UI
    weights: np.ndarray | None = None
    class_average: float | None = None
    target_average: float | None = None
    deviation: float = 0.0           # |achieved - target| in marks
    target_reached: bool = False     # optimal *and* on the target

    @property
    def ok(self) -> bool:
        return self.status == "optimal" and self.weights is not None


def _pct(fraction: float) -> float:
    """Fractions are shown to the lecturer as percentages."""
    return round(float(fraction) * 100, 1)


def _label(names: list[str] | None, index: int) -> str:
    if names and 0 <= index < len(names) and names[index]:
        return f"'{names[index]}'"
    return f"assessment {index + 1}"


def validate_weight_ranges(
    lower_bounds: np.ndarray,
    upper_bounds: np.ndarray,
    names: list[str] | None = None,
) -> np.ndarray:
    """Check the lecturer's ranges and return the effective lower bounds.

    Raises :class:`WeightRangeError` on the first broken rule. The message always
    names the assessment (or the class-wide sum) and the size of the problem so
    the UI can show something actionable instead of crashing.
    """
    lower = np.asarray(lower_bounds, dtype=float)
    upper = np.asarray(upper_bounds, dtype=float)
    if lower.shape != upper.shape:
        raise WeightRangeError("Internal error: minimum and maximum ranges differ in length.")
    if lower.size == 0:
        raise WeightRangeError("This module has no assessments to optimise.")

    for i, (lo, hi) in enumerate(zip(lower, upper)):
        if not np.isfinite(lo) or not np.isfinite(hi):
            raise WeightRangeError(f"The weight range for {_label(names, i)} is not a number.")
        # Rule 1 — no assessment may ever be weighted to zero.
        if lo <= 0.0:
            raise WeightRangeError(
                f"Minimum weight for {_label(names, i)} must be greater than 0% — "
                "every assessment has to carry weight, so no weight may be zero."
            )
        if hi > 100.0 + 1e-9:
            raise WeightRangeError(
                f"Maximum weight for {_label(names, i)} cannot be more than 100% "
                f"(it is {_pct(hi)}%)."
            )
        # Rule 2 — min <= max.
        if lo > hi:
            raise WeightRangeError(
                f"Minimum weight for {_label(names, i)} ({_pct(lo)}%) is above its "
                f"maximum ({_pct(hi)}%). Lower the minimum or raise the maximum."
            )

    effective_lower = np.maximum(lower, MIN_WEIGHT_FRACTION)

    # Rule 3 — feasibility: the ranges must be able to sum to exactly 100%.
    total_min = float(effective_lower.sum())
    total_max = float(upper.sum())
    if total_min > 1.0 + 1e-9:
        raise WeightRangeError(
            f"Infeasible ranges: the minimum weights add up to {_pct(total_min)}%, "
            f"which is {_pct(total_min - 1.0)}% more than 100%. Lower the minimums "
            f"by at least {_pct(total_min - 1.0)}% in total."
        )
    if total_max < 1.0 - 1e-9:
        raise WeightRangeError(
            f"Infeasible ranges: the maximum weights add up to {_pct(total_max)}%, "
            f"which is {_pct(1.0 - total_max)}% less than 100%. Raise the maximums "
            f"by at least {_pct(1.0 - total_max)}% in total."
        )

    return effective_lower


def _repair_sum(x: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> np.ndarray:
    """Nudge ``x`` toward sum(x) == 1 without leaving [lower, upper].

    Used only to build a feasible starting point for SLSQP — the solver still has
    to satisfy the equality constraint itself, this just stops it starting from
    an obviously invalid point when the lecturer's current weights sit outside
    their new ranges.
    """
    x = np.clip(x, lower, upper)
    for _ in range(60):
        diff = 1.0 - float(x.sum())
        if abs(diff) < 1e-12:
            break
        room = (upper - x) if diff > 0 else (x - lower)
        total_room = float(room.sum())
        if total_room <= 1e-12:
            break
        x = np.clip(x + room * (diff / total_room), lower, upper)
    return x


def _starting_point(
    lower: np.ndarray, upper: np.ndarray, initial_weights: np.ndarray | None
) -> np.ndarray:
    if initial_weights is not None:
        candidate = np.asarray(initial_weights, dtype=float)
        if candidate.shape == lower.shape:
            return _repair_sum(candidate, lower, upper)
    return _repair_sum((lower + upper) / 2.0, lower, upper)


def solve_weight_ranges(
    mark_matrix: np.ndarray,
    target_average: float,
    lower_bounds: np.ndarray,
    upper_bounds: np.ndarray,
    initial_weights: np.ndarray | None = None,
    names: list[str] | None = None,
) -> WeightSolution:
    """Solve Algorithm 3 subject to the lecturer's [min%, max%] ranges.

    Never raises for bad input: range problems come back as ``status="infeasible"``
    and solver problems as ``status="failed"``, each with a message written for the
    lecturer. ``status="optimal"`` means the returned weights satisfy every
    constraint (sum == 100%, within range, no zero weight) — that is verified, not
    assumed from the solver's success flag.

    ``mark_matrix``: shape (n_students, n_assessments) of per-assessment marks.
    ``target_average``: desired class average after reweighting.
    ``lower_bounds`` / ``upper_bounds``: per-assessment fractions from the UI.
    """
    mark_matrix = np.asarray(mark_matrix, dtype=float)
    if mark_matrix.ndim != 2 or mark_matrix.shape[1] == 0:
        return WeightSolution(
            status="failed",
            message="There is no assessment plan to optimise yet.",
            target_average=float(target_average),
        )
    if mark_matrix.shape[0] == 0:
        return WeightSolution(
            status="failed",
            message="This module has no students yet, so there is nothing to optimise.",
            target_average=float(target_average),
        )

    try:
        effective_lower = validate_weight_ranges(lower_bounds, upper_bounds, names)
    except WeightRangeError as exc:
        return WeightSolution(
            status="infeasible",
            message=str(exc),
            target_average=float(target_average),
        )

    upper = np.asarray(upper_bounds, dtype=float)
    n_assessments = mark_matrix.shape[1]
    x0 = _starting_point(effective_lower, upper, initial_weights)

    # Published objective (Van der Merwe et al., 2018b): the weight vector whose
    # resulting class average sits closest to the lecturer's target.
    def objective(w: np.ndarray) -> float:
        return float((mark_matrix @ w).mean() - target_average) ** 2

    constraints = [{"type": "eq", "fun": lambda w: float(w.sum()) - 1.0}]
    bounds = [(float(lo), float(hi)) for lo, hi in zip(effective_lower, upper)]

    result = minimize(
        objective,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 300, "ftol": 1e-10},
    )

    if not result.success or result.x is None:
        return WeightSolution(
            status="failed",
            message=(
                "The optimiser did not converge with these ranges "
                f"({result.message}). Try widening the ranges or lowering the target."
            ),
            target_average=float(target_average),
        )

    weights = np.asarray(result.x, dtype=float)
    if weights.shape != (n_assessments,):
        return WeightSolution(
            status="failed",
            message="The optimiser returned an unexpected number of weights.",
            target_average=float(target_average),
        )

    # Verify what came back rather than trusting the success flag.
    if abs(float(weights.sum()) - 1.0) > _SUM_TOLERANCE:
        return WeightSolution(
            status="failed",
            message=(
                "The optimiser could not find weights that add up to 100% within "
                "the ranges you set. Widen the ranges slightly and try again."
            ),
            target_average=float(target_average),
        )
    below = weights < effective_lower - _RANGE_TOLERANCE
    above = weights > upper + _RANGE_TOLERANCE
    if below.any() or above.any():
        bad = int(np.argmax(below | above))
        return WeightSolution(
            status="failed",
            message=(
                f"The optimiser produced a weight for {_label(names, bad)} outside its "
                "allowed range, so the result was discarded. Widen the ranges and try again."
            ),
            target_average=float(target_average),
        )

    class_average = float((mark_matrix @ weights).mean())
    deviation = abs(class_average - float(target_average))
    target_reached = deviation <= _ON_TARGET_TOLERANCE
    if target_reached:
        message = (
            f"The proposed weights put the class on the {target_average:.1f}% target "
            f"(resulting average {class_average:.1f}%)."
        )
    else:
        message = (
            f"The target is not reachable within these ranges: the closest class "
            f"average is {class_average:.1f}%, {deviation:.1f} marks from the "
            f"{target_average:.1f}% target. Widen the ranges or lower the target to "
            "close the gap."
        )

    return WeightSolution(
        status="optimal",
        message=message,
        weights=weights,
        class_average=round(class_average, 2),
        target_average=float(target_average),
        deviation=round(deviation, 2),
        target_reached=target_reached,
    )


def optimise_weights(
    mark_matrix: np.ndarray,
    target_average: float,
    initial_weights: np.ndarray | None = None,
    lower_bounds: np.ndarray | None = None,
    upper_bounds: np.ndarray | None = None,
) -> np.ndarray:
    """Backwards-compatible wrapper returning just the weight vector.

    Prefer :func:`solve_weight_ranges` when the caller needs the solver status or
    a message for the user. Raises ``ValueError`` when the ranges are unsolvable.
    """
    n_assessments = np.asarray(mark_matrix).shape[1] if np.asarray(mark_matrix).ndim == 2 else 0
    lower = (
        np.full(n_assessments, MIN_WEIGHT_FRACTION)
        if lower_bounds is None
        else np.asarray(lower_bounds, dtype=float)
    )
    upper = (
        np.ones(n_assessments)
        if upper_bounds is None
        else np.asarray(upper_bounds, dtype=float)
    )
    solution = solve_weight_ranges(
        mark_matrix,
        target_average,
        lower,
        upper,
        initial_weights=initial_weights,
    )
    if not solution.ok:
        raise ValueError(solution.message)
    return solution.weights
