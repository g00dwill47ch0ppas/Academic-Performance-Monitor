"""
Algorithm 3 — Non-Linear Programming weight optimisation.

Based on Van der Merwe et al. (2018b). Given a class's current per-assessment marks
and a lecturer-specified target class average, computes the assessment weight
combination that would achieve that target.

NOTE ON TECH STACK: this project uses PuLP for Algorithm 1 to match the project's
chosen LP library, but PuLP solves linear/mixed-integer problems only — it cannot
express the non-linear objective this algorithm requires. Reformulating Algorithm 3
as a linear approximation would modify the mathematical model, which the research
proposal (§1.4.6) explicitly rules out ("adopted directly ... not modified").
scipy.optimize is therefore used for this one algorithm only.

# TODO: confirm against source paper —
#   1. Must weights sum to exactly 1 (enforced here as an equality constraint)?
#   2. Are there per-assessment minimum/maximum weight bounds (e.g. no single
#      assessment below 5% or above 50%)? Defaults to [0, 1] per weight here.
"""

import numpy as np
from scipy.optimize import minimize


def optimise_weights(
    mark_matrix: np.ndarray,
    target_average: float,
    initial_weights: np.ndarray | None = None,
) -> np.ndarray:
    """
    mark_matrix: shape (n_students, n_assessments) of average marks per assessment.
    target_average: desired class average p-mark after reweighting.
    Returns: array of shape (n_assessments,) — the optimised weight vector.
    """
    n_assessments = mark_matrix.shape[1]
    x0 = (
        initial_weights
        if initial_weights is not None
        else np.full(n_assessments, 1 / n_assessments)
    )

    def objective(w):
        class_pmarks = mark_matrix @ w
        return (class_pmarks.mean() - target_average) ** 2

    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    bounds = [(0, 1) for _ in range(n_assessments)]

    result = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=constraints)

    if not result.success:
        raise ValueError(f"NLP weight optimisation did not converge: {result.message}")

    return result.x
