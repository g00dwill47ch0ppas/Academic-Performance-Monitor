"""
Algorithm 1 — Linear Programming bounds on a student's achievable p-mark.

Based on Van der Merwe et al. (2018b). Given a student's completed assessment
marks/weights and the weights of remaining (not-yet-written) assessments, this
computes the minimum and maximum p-mark the student could still achieve.

Uses PuLP (matching this project's tech stack) with the bundled CBC solver.

# TODO: confirm against source paper —
#   1. Are remaining marks bounded [0, 100], or does the module use a different scale?
#   2. Is there a cross-assessment constraint (e.g. marks summing to a cap), or is
#      each remaining assessment mark independently bounded?
This implementation assumes independent bounds of [0, 100] per remaining
assessment — the simplest faithful reading of an LP over a weighted sum with no
coupling constraints.
"""

import pulp

from backend.models.student import Assessment, Student


def _solve(remaining: list[Assessment], sense) -> float:
    prob = pulp.LpProblem("pmark_bound", sense)
    variables = [
        pulp.LpVariable(f"y_{i}", lowBound=0, upBound=100) for i in range(len(remaining))
    ]
    prob += pulp.lpSum(v * a.weight for v, a in zip(variables, remaining))
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    return pulp.value(prob.objective)


def compute_pmark_bounds(assessments: list[Assessment]) -> tuple[float, float]:
    """Returns (min_pmark, max_pmark) for a single student."""
    fixed_contribution = sum(
        a.mark * a.weight for a in assessments if a.completed and a.mark is not None
    )
    remaining = [a for a in assessments if not a.completed]

    if not remaining:
        # Nothing left to optimise — p-mark is fixed.
        return round(fixed_contribution, 2), round(fixed_contribution, 2)

    min_val = fixed_contribution + _solve(remaining, pulp.LpMinimize)
    max_val = fixed_contribution + _solve(remaining, pulp.LpMaximize)

    return round(min_val, 2), round(max_val, 2)


def is_at_risk(max_pmark: float, pass_threshold: float) -> bool:
    """FR5 — a student is at-risk if their best-case p-mark can't clear the threshold."""
    return max_pmark < pass_threshold


def compute_bounds_for_student(student: Student) -> tuple[float, float]:
    return compute_pmark_bounds(student.assessments)
