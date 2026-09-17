"""Cohort Planning — Algorithm 3 builder helpers (weight constraints + extremes).

These are presentation-side helpers only: they do not touch the NLP solver's
objective. They support the per-assessment weight-range UI added to the cohort
planning page, and keep the "max weight implying a 0% result" explanation
grounded in the current plan / class data.
"""

from __future__ import annotations

from typing import Any

from backend.algorithms.lp_bounds import compute_pmark_bounds


def lp_extremes_for_assessment(
    student_assessments: list[Any], assessment_name: str
) -> tuple[float, float]:
    """Best- and worst-case p-mark contribution from one assessment across the class.

    Uses the same LP bound machinery as the student detail page, but scoped to a
    single assessment so the UI can say how much of the class's p-mark range a
    given component can still move.
    """
    matching = [a for a in student_assessments if a.name == assessment_name]
    if not matching:
        return 0.0, 0.0
    if any(a.completed for a in matching):
        # Already written — fixed contribution from this student's record.
        entry = next(a for a in matching if a.completed)
        return float(entry.mark * entry.weight), float(entry.mark * entry.weight)
    remaining = [a for a in matching if not a.completed]
    if not remaining:
        return 0.0, 0.0
    # Treat as an LP over the remaining marks only.
    import pulp
    prob_min = pulp.LpProblem("min", pulp.LpMinimize)
    prob_max = pulp.LpProblem("max", pulp.LpMaximize)
    vars_ = [pulp.LpVariable(f"y_{i}", lowBound=0, upBound=100) for i in range(len(remaining))]
    prob_min += pulp.lpSum(v * a.weight for v, a in zip(vars_, remaining))
    prob_max += pulp.lpSum(v * a.weight for v, a in zip(vars_, remaining))
    prob_min.solve(pulp.PULP_CBC_CMD(msg=0))
    prob_max.solve(pulp.PULP_CBC_CMD(msg=0))
    return (
        round(float(pulp.value(prob_min.objective)), 2),
        round(float(pulp.value(prob_max.objective)), 2),
    )


def weight_range_summary(module: Any) -> dict[str, dict[str, float | int]]:
    """One summary record per assessment for the cohort-planning weight UI.

    Each record keeps the assessment name, current weight, and the extremes above
    so the template can explain what happens if a weight is reduced toward zero.
    """
    records: dict[str, dict[str, float | int]] = {}
    all_student_assessments = [
        assessment for student in module.students for assessment in student.assessments
    ]
    for a in module.assessments:
        min_, max_ = lp_extremes_for_assessment(all_student_assessments, a.name)
        records[a.name] = {
            "name": a.name,
            "weight": round(a.weight * 100, 1),
            "min_contribution": min_,
            "max_contribution": max_,
        }
    return records
