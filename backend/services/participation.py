"""
The single source of truth for participation marks ("best N of M").

Van der Merwe et al. (2018b) define a student's participation mark as
p = sum(y_i * w_i) over completed assessments. This prototype extends that with
*droppable* assessments: an assessment TYPE (e.g. "Class Tests") consists of M
items of which only the best N count. With a type weight W, every counted slot is
worth W / N of the final mark, and the counted slots are the top min(k, N) items
by PERCENTAGE (mark / item max), so items with different maxima compare fairly.

Every rule below lives here — routes, algorithms, the at-risk logic and the
templates all call this module, so the rule exists in exactly one place:

    * blank mark  -> not written yet (NOT zero); a recorded 0 is a real mark
    * counted     -> the top min(k, N) completed items by percentage, ties broken
                     by plan order (earliest item first)
    * dropped     -> completed items ranked below the counted ones (only once k > N)
    * accrued     -> sum(counted marks) * W / N          (points, 0-100 scale)
    * standing    -> accrued re-based on the counted slots filled so far (a mean
                     percentage), i.e. the mark on the work that has counted
    * min final   -> remaining items score 0%; lows are then dropped, so the
                     minimum equals the accrued mark exactly
    * max final   -> remaining items score 100%; a strong remaining item can
                     displace a dropped one, so 100s enter the top-N selection

Nothing here rounds: values keep full precision so the algorithms cannot drift.
Rounding happens only at the output edge (Jinja ``|r2``, JS ``fmt2``, export
writers).

# TODO: confirm against source paper — Van der Merwe et al. (2018b) do not define
droppable assessments at all. The rule implemented here is this artefact's own
extension: rank by percentage, take the top N, give each counted slot W / N, and
treat blank marks as “not written”. The ranking key and the tie-break (earliest
item first) are choices made in this project, not readings of the paper.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Marks are on a 0-100 scale (see the module docstring of lp_bounds.py).
MARK_MAX = 100.0


@dataclass
class ItemParticipation:
    """One assessment item for one student, with its counted/dropped verdict."""

    name: str
    type_name: str
    weight: float                 # W — the *type's* weight (fraction of final)
    mark: float | None            # None = not written yet; 0 is a real mark
    completed: bool
    order: int                    # position in the plan, for deterministic ties
    items: int = 1                # M — items in the type
    count_best: int = 1           # N — how many of them count
    item_max: float = MARK_MAX    # max mark for this item
    counted: bool = False
    dropped: bool = False
    index: int = 0                # position in the supplied list

    @property
    def has_mark(self) -> bool:
        return self.completed and self.mark is not None

    @property
    def percentage(self) -> float | None:
        """Mark as a percentage of the item's maximum.

        Items are ranked on PERCENTAGE, never on raw marks, so items with
        different maxima compare fairly (marks are 0-100 in this prototype, so a
        100-mark item's percentage is its mark).
        """
        if not self.has_mark:
            return None
        maximum = self.item_max if self.item_max else MARK_MAX
        return float(self.mark) / maximum * MARK_MAX

    @property
    def slot_weight(self) -> float:
        """Fraction of the final mark one counted slot of this type is worth."""
        return self.weight / max(1, self.count_best)


@dataclass
class TypeParticipation:
    """Aggregated result for one assessment type (M items, best N)."""

    name: str
    weight: float                 # W
    items: int                    # M
    count_best: int               # N
    records: list[ItemParticipation] = field(default_factory=list)
    completed: int = 0            # k
    counted: list[ItemParticipation] = field(default_factory=list)
    dropped: list[ItemParticipation] = field(default_factory=list)
    remaining: list[ItemParticipation] = field(default_factory=list)
    accrued: float = 0.0          # points contributed so far
    standing: float | None = None  # accrued re-based on counted slots so far
    max_achievable: float = 0.0
    min_achievable: float = 0.0

    @property
    def slot_weight(self) -> float:
        return self.weight / max(1, self.count_best)

    @property
    def remaining_slots(self) -> int:
        """Counted slots of this type that are not filled yet."""
        return max(0, self.count_best - len(self.counted))

    @property
    def skippable_remaining(self) -> int:
        """Remaining items that may go unassessed without losing a counted slot.

        A remaining item can be skipped only while at least ``count_best`` items
        (completed ones first) still fill the counted slots.
        """
        return max(0, self.items - max(self.completed, self.count_best))


@dataclass
class Participation:
    """Whole-student result across every assessment type."""

    types: list[TypeParticipation] = field(default_factory=list)
    records: list[ItemParticipation] = field(default_factory=list)
    accrued: float = 0.0          # participation earned so far (points, 0-100)
    standing: float | None = None  # percentage over the work that has counted
    min_final: float = 0.0        # feasible region lower end (= accrued)
    max_final: float = 0.0        # feasible region upper end

    @property
    def remaining_items(self) -> list[ItemParticipation]:
        return [r for r in self.records if not r.has_mark]

    @property
    def counted_items(self) -> list[ItemParticipation]:
        return [r for r in self.records if r.counted]

    @property
    def dropped_items(self) -> list[ItemParticipation]:
        return [r for r in self.records if r.dropped]

    @property
    def remaining_slots(self) -> int:
        return sum(t.remaining_slots for t in self.types)

    @property
    def skippable_remaining(self) -> int:
        return sum(t.skippable_remaining for t in self.types)

    @property
    def counted_weight(self) -> float:
        """Fraction of the final mark covered by counted slots filled so far."""
        return sum(r.slot_weight for r in self.counted_items)


def _item_of(assessment, index: int) -> ItemParticipation:
    """Adapt anything shaped like an assessment into an ItemParticipation."""
    group = getattr(assessment, "group", "") or getattr(assessment, "name", "")
    return ItemParticipation(
        name=assessment.name,
        type_name=group,
        weight=float(getattr(assessment, "weight", 0.0) or 0.0),
        mark=assessment.mark,
        completed=bool(assessment.completed),
        order=index,
        items=int(getattr(assessment, "items", 1) or 1),
        count_best=int(getattr(assessment, "count_best", 1) or 1),
        item_max=float(getattr(assessment, "item_max", MARK_MAX) or MARK_MAX),
        index=index,
    )


def _group_key(record: ItemParticipation) -> str:
    # M == N == 1 means the item is its own type, exactly as before this rule existed.
    if record.items <= 1 and record.count_best <= 1:
        return record.name
    return record.type_name or record.name


def _analyse_type(name: str, records: list[ItemParticipation]) -> TypeParticipation:
    weight = records[0].weight
    items = max(len(records), max(r.items for r in records))
    count_best = max(1, min(max(r.count_best for r in records), items))

    result = TypeParticipation(
        name=name, weight=weight, items=items, count_best=count_best, records=records
    )
    done = [r for r in records if r.has_mark]
    result.completed = len(done)
    result.remaining = [r for r in records if not r.has_mark]

    # Rank by percentage, then by plan order (earliest first) so ties are stable.
    ranked = sorted(done, key=lambda r: (-r.percentage, r.order))
    result.counted = ranked[: min(len(done), count_best)]
    result.dropped = ranked[count_best:]
    for r in result.counted:
        r.counted = True
    for r in result.dropped:
        r.dropped = True

    slot = result.slot_weight
    result.accrued = sum(r.percentage * slot for r in result.counted)
    result.min_achievable = result.accrued  # remaining zeros are dropped; they never lower it

    # Best case: remaining items score 100% and may displace a dropped item.
    pool = [r.percentage for r in done] + [MARK_MAX] * len(result.remaining)
    pool.sort(reverse=True)
    result.max_achievable = sum(pool[:count_best]) * slot

    counted_slots_filled = len(result.counted)
    result.standing = (
        result.accrued / (counted_slots_filled * slot)
        if counted_slots_filled and slot > 0
        else None
    )
    return result


def analyse(items) -> Participation:
    """Apply the best-N-of-M rule to a flat list of assessment items.

    The list may be a student's records or a module plan; items are grouped by
    their type (``group``) unless they are standalone (M = N = 1), in which case
    each item is its own type — which is exactly the pre-drop behaviour.
    """
    records = [_item_of(a, i) for i, a in enumerate(items)]
    grouped: dict[str, list[ItemParticipation]] = {}
    for record in records:
        grouped.setdefault(_group_key(record), []).append(record)

    result = Participation(records=records)
    for name, group_records in grouped.items():
        result.types.append(_analyse_type(name, group_records))

    result.accrued = sum(t.accrued for t in result.types)
    result.min_final = sum(t.min_achievable for t in result.types)
    result.max_final = sum(t.max_achievable for t in result.types)
    counted_weight = sum(r.slot_weight for r in result.counted_items)
    result.standing = result.accrued / counted_weight if counted_weight > 0 else None
    return result


# --------------------------------------------------------------------------- #
# Convenience wrappers — the API routes, algorithms and templates use.
# --------------------------------------------------------------------------- #
def final_participation(items) -> float:
    """The participation mark accrued so far (points, 0-100 scale)."""
    return analyse(items).accrued


def current_standing(items) -> float | None:
    """Accrued mark re-based on the counted slots filled so far (percentage)."""
    return analyse(items).standing


def min_max_final(items) -> tuple[float, float]:
    """The feasible region [min, max] of the final participation mark."""
    result = analyse(items)
    return result.min_final, result.max_final


def final_with_marks(items, overrides: dict[str, float | None] | None = None):
    """Recompute the final participation with specific items overridden.

    ``overrides`` maps an item name to the mark it would score (None = still not
    written). Used by the projection code to answer "what if every remaining item
    scores x?" without duplicating the best-N rule.
    """
    overrides = overrides or {}
    adjusted = []
    for item in items:
        if item.name in overrides:
            mark = overrides[item.name]
            adjusted.append(
                _Override(item=item, mark=mark, completed=mark is not None)
            )
        else:
            adjusted.append(item)
    return analyse(adjusted)


class _Override:
    """A shallow copy of an assessment with one field replaced (keeps the shape)."""

    def __init__(self, item, mark, completed):
        self.name = item.name
        self.weight = item.weight
        self.mark = mark
        self.completed = completed
        self.group = getattr(item, "group", "")
        self.items = getattr(item, "items", 1)
        self.count_best = getattr(item, "count_best", 1)
        self.item_max = getattr(item, "item_max", MARK_MAX)
