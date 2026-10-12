"""Tests for the single participation rule engine (best N of M).

Every case the task calls out is covered here: N = M, N = 1, k < N, k = N, k > N,
ties, items with different maxima, blank vs zero, 10-of-12 attendance, the worked
example, and a student with nothing recorded.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from backend.algorithms.participation_plan import (
    build_projection,
    feasible_region,
    required_uniform_percentage,
)
from backend.models.student import Assessment
from backend.services.participation import (
    analyse,
    current_standing,
    final_participation,
    final_with_marks,
    min_max_final,
)


def items(marks, group="Tests", weight=0.3, items_count=3, count_best=2, maxima=None):
    """Build a type's item records; a None mark means 'not written yet'."""
    records = []
    for i, mark in enumerate(marks):
        records.append(
            Assessment(
                name=f"{group.replace(' ', '_')}_{i + 1}",
                weight=weight,
                mark=mark,
                completed=mark is not None,
                group=group,
                items=items_count,
                count_best=count_best,
                item_max=(maxima[i] if maxima else 100.0),
            )
        )
    return records


# --------------------------------------------------------------------------- #
# N = M (the default: nothing is dropped, behaviour is unchanged)
# --------------------------------------------------------------------------- #
def test_n_equals_m_changes_nothing():
    records = items([60, 80, 50], items_count=3, count_best=3, weight=0.3)
    result = analyse(records)
    assert result.accrued == pytest.approx((60 + 80 + 50) * 0.3 / 3)
    assert result.standing == pytest.approx((60 + 80 + 50) / 3)
    assert result.dropped_items == []
    assert len(result.counted_items) == 3

    # M = N = 1 is the pre-drop behaviour: p = mark * weight.
    single = [Assessment("Test 1", 0.5, 80, True), Assessment("Test 2", 0.5, 60, True)]
    assert final_participation(single) == pytest.approx(70.0)
    assert min_max_final(single) == (70.0, 70.0)


# --------------------------------------------------------------------------- #
# N = 1
# --------------------------------------------------------------------------- #
def test_n_equals_one_keeps_only_the_best_item():
    records = items([40, 90, 70], items_count=3, count_best=1, weight=0.2)
    result = analyse(records)
    assert [i.name for i in result.counted_items] == ["Tests_2"]
    assert sorted(i.name for i in result.dropped_items) == ["Tests_1", "Tests_3"]
    assert result.accrued == pytest.approx(90 * 0.2)
    assert result.standing == pytest.approx(90.0)
    assert result.remaining_slots == 0


# --------------------------------------------------------------------------- #
# k < N, k = N, k > N
# --------------------------------------------------------------------------- #
def test_k_below_n_counts_everything_written():
    result = analyse(items([60, 80, None], count_best=2))
    assert len(result.counted_items) == 2
    assert result.dropped_items == []
    assert result.types[0].remaining_slots == 0
    assert result.accrued == pytest.approx((60 + 80) * 0.3 / 2)


def test_k_equals_n_drops_nothing_yet():
    result = analyse(items([60, 80, None], count_best=2))
    assert result.types[0].completed == 2
    assert result.dropped_items == []
    assert result.standing == pytest.approx(70.0)


def test_k_greater_than_n_drops_the_lowest():
    result = analyse(items([60, 80, 50], count_best=2))
    assert [i.name for i in result.dropped_items] == ["Tests_3"]
    # Counted items keep plan order for display; the *ranking* is what decides
    # which of them are counted at all.
    assert [i.name for i in result.counted_items] == ["Tests_1", "Tests_2"]
    assert result.standing == pytest.approx(70.0)


# --------------------------------------------------------------------------- #
# The worked example from the brief, verbatim
# --------------------------------------------------------------------------- #
def test_worked_example_best_two_of_three_tests():
    # Test 1 = 60%, Test 2 = 80% -> both count, standing 70%.
    two = analyse(items([60, 80, None], count_best=2, weight=0.3))
    assert two.standing == pytest.approx(70.0)

    # Test 3 = 50% -> the 50 is dropped and the standing stays at 70%.
    low = analyse(items([60, 80, 50], count_best=2, weight=0.3))
    assert low.standing == pytest.approx(70.0)
    assert low.dropped_items[0].percentage == 50.0

    # Test 3 = 90% -> the 60 is dropped and the standing becomes 85%.
    high = analyse(items([60, 80, 90], count_best=2, weight=0.3))
    assert high.standing == pytest.approx(85.0)
    assert high.dropped_items[0].name == "Tests_1"


# --------------------------------------------------------------------------- #
# Ties and item maxima
# --------------------------------------------------------------------------- #
def test_ties_break_on_earliest_item_first():
    result = analyse(items([70, 70, None], count_best=1))
    assert [i.name for i in result.counted_items] == ["Tests_1"]
    assert [i.name for i in result.dropped_items] == ["Tests_2"]


def test_ranking_uses_percentage_not_raw_marks():
    # A 40/50 item (80%) must beat a 70/100 item (70%), despite the smaller mark.
    records = items(
        [40, 70],
        items_count=2,
        count_best=1,
        weight=0.4,
        maxima=[50.0, 100.0],
    )
    result = analyse(records)
    assert result.counted_items[0].name == "Tests_1"
    assert result.counted_items[0].percentage == pytest.approx(80.0)
    assert result.accrued == pytest.approx(80 * 0.4)


# --------------------------------------------------------------------------- #
# Blank vs zero
# --------------------------------------------------------------------------- #
def test_blank_is_not_zero():
    zero = analyse(items([0, 80, None], count_best=2))
    blank = analyse(items([None, 80, None], count_best=2))

    # A recorded 0 is a real mark: it fills a counted slot and drags the standing
    # down to 40%. A blank item is simply not written yet, so the standing stays
    # at 80% and the slot is still open.
    assert zero.types[0].completed == 2
    assert blank.types[0].completed == 1
    assert zero.standing == pytest.approx(40.0)
    assert blank.standing == pytest.approx(80.0)
    assert zero.types[0].remaining_slots == 0
    assert blank.types[0].remaining_slots == 1
    assert len(zero.types[0].remaining) == 1
    assert len(blank.types[0].remaining) == 2


def test_zero_marks_are_real_and_can_be_dropped():
    result = analyse(items([0, 0, 90], count_best=2))
    assert result.types[0].completed == 3
    # Top 2 of {0, 0, 90}: the 90 and the earliest of the two zeros count.
    assert [i.name for i in result.dropped_items] == ["Tests_2"]
    assert result.standing == pytest.approx(45.0)

    # A third real mark pushes both zeros out.
    later = analyse(items([0, 0, 90, 95], count_best=2, items_count=4))
    assert sorted(i.name for i in later.dropped_items) == ["Tests_1", "Tests_2"]
    assert later.standing == pytest.approx(92.5)


# --------------------------------------------------------------------------- #
# 10 best of 12 attendance sessions
# --------------------------------------------------------------------------- #
def test_ten_of_twelve_attendance():
    marks = [100] * 10 + [None, None]
    records = items(
        marks, group="Attendance", weight=0.2, items_count=12, count_best=10
    )
    result = analyse(records)
    assert result.accrued == pytest.approx(20.0)
    assert result.remaining_slots == 0
    assert result.types[0].skippable_remaining == 2

    # Writing two poor sessions changes nothing — the two best 100s still count.
    filled = items(
        [100] * 10 + [10, 20], group="Attendance", weight=0.2, items_count=12,
        count_best=10,
    )
    assert analyse(filled).accrued == pytest.approx(20.0)
    assert len(analyse(filled).dropped_items) == 2


# --------------------------------------------------------------------------- #
# Nothing recorded
# --------------------------------------------------------------------------- #
def test_student_with_nothing_recorded():
    result = analyse(items([None, None, None], count_best=2))
    assert result.accrued == 0.0
    assert result.standing is None
    assert current_standing(items([None, None, None], count_best=2)) is None
    assert result.remaining_slots == 2
    # Two counted slots at 100% of a 0.3-weight type = 30 marks.
    assert result.max_final == pytest.approx(30.0)
    assert result.min_final == 0.0


# --------------------------------------------------------------------------- #
# Region and projection
# --------------------------------------------------------------------------- #
def test_region_uses_drops_at_both_ends():
    records = items([60, 80, None], count_best=2, weight=0.3)
    region = feasible_region(records)
    assert region.minimum == pytest.approx(21.0)
    # Best case: the remaining item scores 100 and displaces nothing (only 2 written).
    assert region.maximum == pytest.approx(27.0)
    assert region.is_point is False


def test_region_with_an_already_dropped_item_can_improve():
    # Two written, both counted; a third item at 100 must displace the 60.
    records = items([60, 80, None], count_best=2, weight=0.3)
    assert feasible_region(records).maximum == pytest.approx((80 + 100) * 0.3 / 2)


def test_region_is_a_point_when_nothing_remains():
    records = items([60, 80, 90], count_best=2)
    region = feasible_region(records)
    assert region.is_point is True
    assert region.minimum == region.maximum == pytest.approx(85 * 0.3)


def test_target_at_both_ends_of_the_region():
    records = items([60, 80, None], count_best=2, weight=0.3)
    region = feasible_region(records)
    at_min = build_projection(records, region.minimum)
    at_max = build_projection(records, region.maximum)
    assert at_min.required_percentage == pytest.approx(0.0)
    assert at_max.required_percentage == pytest.approx(100.0)


def test_mid_region_target_recomputes_to_the_target():
    records = items([60, 80, None], count_best=2, weight=0.3)
    region = feasible_region(records)
    target = (region.minimum + region.maximum) / 2
    projection = build_projection(records, target)
    assert projection.reachable
    x = projection.required_percentage
    assert x is not None
    overrides = {r.name: x for r in records if r.mark is None}
    achieved = final_with_marks(records, overrides).accrued
    assert achieved == pytest.approx(target, abs=1e-6)


def test_out_of_region_target_is_not_planned():
    records = items([60, 80, None], count_best=2, weight=0.3)
    above = build_projection(records, 99.0)
    assert above.reachable is False
    assert above.required_percentage is None
    assert "above the maximum" in above.summary
    assert required_uniform_percentage(records, 99.0) is None


def test_projection_includes_every_remaining_item():
    records = items([60, 80, None], count_best=2, weight=0.3) + [
        Assessment("Practical", 0.1, None, False)
    ]
    projection = build_projection(records, 25.0)
    remaining_names = {r.name for r in records if r.mark is None}
    assert {item.name for item in projection.items} == remaining_names
    for item in projection.items:
        assert item.percentage == pytest.approx(projection.required_percentage)


def test_projection_says_when_an_item_can_be_skipped():
    # One 100% already counted, one slot still open, so only one of the two
    # remaining tests must actually be written.
    records = items([100, None, None], group="Tests", weight=0.3, items_count=3,
                    count_best=2)
    projection = build_projection(records, 27.0)
    assert projection.required_percentage == pytest.approx(80.0)
    assert any("skip" in note for note in projection.notes), projection.notes
    assert any("Tests" in note for note in projection.notes)


def test_projection_says_when_nothing_can_be_skipped():
    records = items(
        [50, 40, None, None], group="Tests", weight=0.3, items_count=4, count_best=2
    )
    # Both remaining tests must be written: two of the four items count and both
    # open ones have to carry the target between them.
    projection = build_projection(records, 25.0)
    assert projection.required_percentage is not None
    assert any(
        note.startswith("Tests: none of the 2 still-open items can be skipped")
        for note in projection.notes
    ), projection.notes


def test_skipping_an_item_keeps_the_target_reachable():
    """The note explains what the remaining items need once one is skipped."""
    records = items([100, None, None], group="Tests", weight=0.3, items_count=3,
                    count_best=2)
    projection = build_projection(records, 27.0)
    # One 100% is banked and only one more slot needs filling, so scoring 80% on
    # either of the two open tests reaches the target — the other can be skipped.
    assert projection.required_percentage == pytest.approx(80.0, abs=1e-4)
    note = next(n for n in projection.notes if "you can skip" in n)
    assert "the other 1 scores at least 80%" in note, note
