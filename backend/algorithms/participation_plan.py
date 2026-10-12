"""
Algorithm 2 — Participation planning from a target and a feasible region.

Van der Merwe et al. (2018b) enumerate mark combinations that achieve a
percentage *improvement* over the current p-mark, treating not-yet-written
assessments as zero. That no longer fits this artefact: the lecturer now picks a
target final participation mark (not an increase), the feasible region is computed
first, every remaining item is a variable, and droppable ("best N of M") types must
be respected while planning.

WHAT REPLACED WHAT (documented in docs/technical_specification.md)
    * feasible region: [min, max] from ``backend.services.participation``
    * required uniform percentage x: solved by bisection on x -> final(x), which is
      monotone non-decreasing, so the solve is exact to a tolerance far smaller
      than any mark a lecturer can enter. The drop rule is applied inside every
      evaluation, never approximated.
    * optional items: the drop rule means some remaining items need not be written
      at all; that is computed per type and reported in plain language.

The combinatorial scenario table of the old implementation is gone: with drops it
could not be adapted cleanly (a scenario is no longer a simple mark vector — the
*dropping* of a mark is part of the outcome), and enumerating 21^(items) rows was
never going to include the slowest case a lecturer cares about. No dead code is
left behind.

# TODO: confirm against source paper — the paper's Algorithm 2 plans from a
# percentage improvement and assumes every remaining assessment is included at a
# chosen mark. This implementation plans from an absolute target and adds the
# "what can I skip?" analysis, which the paper does not define.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.models.student import Assessment
from backend.services.participation import (
    MARK_MAX,
    Participation,
    analyse,
    final_with_marks,
)
from backend.services.rounding import fmt2

#: Bisection stops once the required percentage is this precise (in marks).
TOLERANCE = 1e-6
#: Safety cap: final(x) is monotone, so 200 halvings cover [0, 100] far beyond it.
MAX_ITERATIONS = 200


@dataclass
class Region:
    """The feasible region of the final participation mark."""

    minimum: float
    maximum: float
    current: float                 # the accrued mark (== minimum)
    pass_threshold: float | None = None

    @property
    def is_point(self) -> bool:
        """True when nothing remains to be written (region collapses to a point)."""
        return abs(self.maximum - self.minimum) < 1e-9

    @property
    def can_pass(self) -> bool:
        if self.pass_threshold is None:
            return True
        return self.maximum >= self.pass_threshold


@dataclass
class RequiredItem:
    """One remaining item's requirement for the chosen target."""

    name: str
    type_name: str
    percentage: float              # minimum uniform percentage for this item
    raw_mark: float                # equivalent raw mark (out of the item's max)


@dataclass
class Projection:
    """What every remaining item must reach for the chosen target."""

    target: float
    required_percentage: float | None      # None = target not reachable
    items: list[RequiredItem] = field(default_factory=list)
    summary: str = ""
    notes: list[str] = field(default_factory=list)
    reachable: bool = True
    region: Region | None = None

    @property
    def is_zero_effort(self) -> bool:
        return self.required_percentage is not None and self.required_percentage <= 0.0


def feasible_region(
    assessments: list[Assessment], pass_threshold: float | None = None
) -> Region:
    """The [min, max] range of reachable final participation marks."""
    result = analyse(assessments)
    return Region(
        minimum=result.min_final,
        maximum=result.max_final,
        current=result.accrued,
        pass_threshold=pass_threshold,
    )


def _final_with_uniform(items: list[Assessment], x: float) -> float:
    """Final participation when every remaining item scores exactly x."""
    overrides = {item.name: x for item in items if not (item.completed and item.mark is not None)}
    return final_with_marks(items, overrides).accrued


def required_uniform_percentage(
    assessments: list[Assessment], target: float, tolerance: float = TOLERANCE
) -> float | None:
    """The smallest x every remaining item must reach so the final >= target.

    ``final(x)`` is monotone non-decreasing in x, so bisection is exact. Returns
    None when the target is above the feasible maximum (or already at the top).
    """
    if _final_with_uniform(assessments, MARK_MAX) < target - tolerance:
        return None
    if _final_with_uniform(assessments, 0.0) >= target - tolerance:
        return 0.0

    low, high = 0.0, MARK_MAX
    for _ in range(MAX_ITERATIONS):
        mid = (low + high) / 2.0
        if _final_with_uniform(assessments, mid) >= target:
            high = mid
        else:
            low = mid
        if high - low < tolerance:
            break
    return high


def _uniform_for(assessments: list[Assessment], target: float, skipped: set[str]) -> float | None:
    """Minimum level on every remaining item that is NOT skipped.

    Skipped items stay at 0 and are dropped by the best-N rule; the rest share a
    single required level, solved by the same monotone bisection. Returns None
    when even 100% on the active items cannot reach the target.
    """
    remaining = [
        item for item in assessments if not (item.completed and item.mark is not None)
    ]

    def value(level: float) -> float:
        overrides = {
            item.name: (0.0 if item.name in skipped else level) for item in remaining
        }
        return final_with_marks(assessments, overrides).accrued

    if value(MARK_MAX) < target - TOLERANCE:
        return None
    if value(0.0) >= target - TOLERANCE:
        return 0.0

    low, high = 0.0, MARK_MAX
    for _ in range(MAX_ITERATIONS):
        mid = (low + high) / 2.0
        if value(mid) >= target:
            high = mid
        else:
            low = mid
        if high - low < TOLERANCE:
            break
    return high


def _skippable_notes(assessments: list[Assessment], target: float) -> list[str]:
    """Plain-English notes about items the student may leave unassessed.

    The drop rule means a remaining item need not be written at all. For each
    type the note reports how many of its open items can stay unwritten, and what
    the other items then have to score — because skipping raises the level the
    rest must reach, that level is solved again for each skip count rather than
    assumed to be the uniform one.
    """
    result: Participation = analyse(assessments)
    notes: list[str] = []
    for type_result in result.types:
        remaining = [r for r in type_result.records if not r.has_mark]
        if not remaining:
            continue

        skippable = 0
        level_after = None
        for candidate in range(1, len(remaining) + 1):
            skipped = {record.name for record in remaining[:candidate]}
            level = _uniform_for(assessments, target, skipped)
            if level is None:
                break
            skippable = candidate
            level_after = level

        open_word = "item" if len(remaining) == 1 else "items"
        if skippable <= 0 or level_after is None:
            notes.append(
                f"{type_result.name}: none of the {len(remaining)} still-open "
                f"{open_word} can be skipped — the target needs every one of them "
                f"(only the best {type_result.count_best} of {type_result.items} "
                f"count, but nothing is spare yet)."
            )
            continue

        left = len(remaining) - skippable
        word = "item" if skippable == 1 else "items"
        if level_after <= 0:
            notes.append(
                f"{type_result.name}: the marks already recorded secure this target, so "
                f"all {len(remaining)} remaining {open_word} can stay unassessed."
            )
        elif left == 0:
            pointer = "this one" if skippable == 1 else "these"
            notes.append(
                f"{type_result.name}: you can leave {pointer} unassessed — every other "
                f"remaining item then needs at least {fmt2(level_after)}%."
            )
        else:
            verb = "scores" if left == 1 else "score"
            notes.append(
                f"{type_result.name}: you can skip {skippable} {word} and still reach "
                f"this target if the other {left} {verb} at least {fmt2(level_after)}% "
                f"(only the best {type_result.count_best} of {type_result.items} count)."
            )
    return notes


def _plain_summary(items: list[RequiredItem], x: float, target: float) -> str:
    if not items:
        return (
            f"Nothing is left to write, so the final participation mark stays at "
            f"{fmt2(target)}%."
        )
    return (
        f"To reach {fmt2(target)}%, you need at least {fmt2(x)}% on each of the "
        f"{len(items)} remaining item{'s' if len(items) != 1 else ''}."
    )


def build_projection(
    assessments: list[Assessment],
    target: float,
    pass_threshold: float | None = None,
) -> Projection:
    """Plan what every remaining item must score to reach ``target``.

    ``target`` is an absolute final participation percentage and is expected to
    already be inside the feasible region; callers validate that at the boundary
    (the UI restricts the slider to the region and the route re-checks).
    """
    region = feasible_region(assessments, pass_threshold)
    projection = Projection(target=target, required_percentage=None, region=region)

    remaining = [
        item for item in assessments if not (item.completed and item.mark is not None)
    ]
    if not remaining:
        projection.reachable = target <= region.maximum + TOLERANCE
        projection.required_percentage = 0.0 if projection.reachable else None
        projection.summary = (
            f"Nothing remains to be written — the final participation mark is fixed "
            f"at {fmt2(region.maximum)}%."
        )
        return projection

    x = required_uniform_percentage(assessments, target)
    if x is None:
        projection.reachable = False
        projection.summary = (
            f"{fmt2(target)}% is above the maximum reachable mark of "
            f"{fmt2(region.maximum)}%, so it cannot be planned for."
        )
        return projection

    projection.required_percentage = x
    projection.items = [
        RequiredItem(
            name=item.name,
            type_name=getattr(item, "group", "") or item.name,
            percentage=x,
            raw_mark=x / MARK_MAX * float(getattr(item, "item_max", MARK_MAX) or MARK_MAX),
        )
        for item in remaining
    ]
    projection.summary = _plain_summary(projection.items, x, target)
    projection.notes = _skippable_notes(assessments, target)
    if x <= 0:
        projection.notes.insert(
            0,
            "The target is already secured by the marks recorded so far — the "
            "remaining items cannot pull it below it.",
        )
    return projection
