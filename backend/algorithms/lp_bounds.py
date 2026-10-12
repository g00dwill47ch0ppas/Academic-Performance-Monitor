"""
Algorithm 1 — min/max bounds on a student's achievable participation mark.

Based on Van der Merwe et al. (2018b), which bounds each remaining assessment's
mark in [0, 100] and solves two LPs over the weighted sum.

Since droppable assessments ("best N of M") were added, the feasible set is no
longer a box that a plain LP can describe: which assessments *count* depends on
the ranking of the marks, so the objective is piecewise-linear. The extrema are
nevertheless exact and closed-form, so this module no longer asks a solver to
rediscover arithmetic:

    min = the accrued mark  (every remaining item scores 0 and the lows are
          then dropped, so no achievable mark can be lower)
    max = the top N of (completed marks + 100% for every remaining item),
          because a strong remaining item may displace a dropped one

Both come from ``backend.services.participation`` — the single place the drop
rule lives. There is deliberately no duplicated bound logic here; any route,
export or template that needs a range calls these functions or the service.

# TODO: confirm against source paper — Van der Merwe et al. (2018b) formulate the
# bounds as two LPs over independent [0, 100] marks per remaining assessment.
# That formulation is a special case of the closed form used here (it is what
# this returns when every type has N = M, i.e. nothing is dropped). The paper does
# not cover droppable assessments, so the drop extension is this artefact's own
# and is flagged rather than presented as the published model.
"""

from backend.models.student import Assessment, Student
from backend.services.participation import min_max_final


def compute_pmark_bounds(assessments: list[Assessment]) -> tuple[float, float]:
    """Returns (min_pmark, max_pmark) for a single student.

    Full precision — callers round at the output edge (Jinja ``|r2`` / ``fmt2``).
    """
    return min_max_final(assessments)


def is_at_risk(max_pmark: float, pass_threshold: float) -> bool:
    """FR5 — a student is at-risk if their best-case p-mark can't clear the threshold."""
    return max_pmark < pass_threshold


def compute_bounds_for_student(student: Student) -> tuple[float, float]:
    return compute_pmark_bounds(student.assessments)
