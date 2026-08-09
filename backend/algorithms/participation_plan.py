"""
Algorithm 2 — Participation Planning.

Based on Van der Merwe et al. (2018b). Generates feasible mark combinations across
a student's remaining assessments that achieve a specified percentage improvement
over their current p-mark, and reports what's required in each scenario.

Pure combinatorics (itertools) — no LP/NLP solver needed for this algorithm.

# TODO: confirm against source paper —
#   1. What increment/step size does the paper use when enumerating scenarios
#      (this defaults to 5-point steps, i.e. 0, 5, 10 ... 100)?
#   2. Is "percentage improvement" relative to current p-mark, or an absolute
#      target p-mark? This implementation assumes relative improvement.
"""

from itertools import product

from backend.models.student import Assessment


def generate_participation_plan(
    assessments: list[Assessment],
    current_pmark: float,
    target_improvement_pct: float,
    step: float = 5.0,
    max_scenarios: int = 20,
) -> list[dict]:
    """
    Returns a list of scenarios, each a dict:
        {"<assessment_name>": required_mark, ..., "resulting_pmark": float}
    that meet or exceed the target p-mark, capped at max_scenarios for readability.
    """
    fixed_contribution = sum(
        a.mark * a.weight for a in assessments if a.completed and a.mark is not None
    )
    remaining = [a for a in assessments if not a.completed]
    if not remaining:
        return []

    target_pmark = current_pmark * (1 + target_improvement_pct / 100)
    mark_options = list(range(0, 101, int(step)))
    scenarios = []

    for combo in product(mark_options, repeat=len(remaining)):
        resulting_pmark = fixed_contribution + sum(
            mark * a.weight for mark, a in zip(combo, remaining)
        )
        if resulting_pmark >= target_pmark:
            scenario = {a.name: mark for a, mark in zip(remaining, combo)}
            scenario["resulting_pmark"] = round(resulting_pmark, 2)
            scenarios.append(scenario)
            if len(scenarios) >= max_scenarios:
                break

    return scenarios
