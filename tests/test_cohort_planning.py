"""Cohort planning — Algorithm 3 constrained by lecturer weight ranges.

Covers both layers:
  * the solver in ``backend.algorithms.nlp_weights`` (weights sum to 100%, sit
    inside the requested ranges and are never zero, infeasible input is reported
    through the status rather than raised), and
  * the ``/cohort`` route (hard rules rejected with a clear message, the target
    slider and ranges submitting together, solver status surfaced on the page).
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend import create_app
from backend.algorithms.nlp_weights import (
    WeightRangeError,
    solve_weight_ranges,
    validate_weight_ranges,
)

# The bundled CS101 sample plan: 15% + 15% + 20% + 20% + 15% + 15% = 100%.
DEFAULT_RANGES = {
    "Class Test 1": (10.0, 25.0),
    "Class Test 2": (10.0, 25.0),
    "Assignment 1": (10.0, 30.0),
    "Assignment 2": (10.0, 30.0),
    "Practical": (5.0, 20.0),
    "Attendance": (5.0, 20.0),
}


def _client():
    return create_app().test_client()


def _form(target: str | None = "62", ranges: dict | None = None, **extra) -> dict:
    """Build a cohort-planning form submission (target + one min/max per assessment)."""
    data: dict[str, str] = {}
    if target is not None:
        data["target_average"] = target
    for name, (low, high) in (ranges or DEFAULT_RANGES).items():
        data[f"min_{name}"] = str(low)
        data[f"max_{name}"] = str(high)
    data.update(extra)
    return data


# --------------------------------------------------------------------------- #
# Solver level
# --------------------------------------------------------------------------- #
def _marks() -> np.ndarray:
    return np.array([[80.0, 60.0, 50.0], [70.0, 50.0, 40.0], [90.0, 40.0, 70.0]])


def test_solution_sums_to_100_percent_and_respects_ranges():
    lower = np.array([0.10, 0.10, 0.10])
    upper = np.array([0.60, 0.60, 0.60])

    solution = solve_weight_ranges(_marks(), 65.0, lower, upper, names=["A", "B", "C"])

    assert solution.status == "optimal"
    assert solution.weights is not None
    assert np.isclose(solution.weights.sum(), 1.0, atol=1e-4)
    assert np.all(solution.weights >= lower - 1e-6)
    assert np.all(solution.weights <= upper + 1e-6)
    assert np.all(solution.weights > 0)  # no assessment may be weighted to zero


def test_no_weight_is_zero_when_the_minimum_is_the_one_percent_floor():
    lower = np.full(3, 0.01)  # lecturer asked for the 1% floor
    upper = np.array([0.90, 0.90, 0.90])

    solution = solve_weight_ranges(_marks(), 65.0, lower, upper, names=["A", "B", "C"])

    assert solution.status == "optimal"
    assert np.all(solution.weights > 0)
    # A zero is impossible: no weight may undercut the strict positive floor.
    assert np.all(solution.weights >= 0.01 - 1e-6)


def test_zero_minimum_is_rejected_by_validation():
    with pytest.raises(WeightRangeError, match="greater than 0%"):
        validate_weight_ranges(
            np.array([0.0, 0.5]), np.array([0.5, 0.5]), ["Test 1", "Test 2"]
        )


def test_minimum_above_maximum_is_rejected_by_validation():
    with pytest.raises(WeightRangeError, match="above its maximum"):
        validate_weight_ranges(
            np.array([0.5, 0.4]), np.array([0.3, 0.6]), ["Test 1", "Test 2"]
        )


def test_infeasible_ranges_come_back_as_a_status_not_an_exception():
    # Minimums add up to 120% — 20% too much.
    lower = np.array([0.4, 0.4, 0.4])
    upper = np.array([0.5, 0.5, 0.5])

    solution = solve_weight_ranges(_marks(), 65.0, lower, upper, names=["A", "B", "C"])

    assert solution.status == "infeasible"
    assert solution.weights is None
    assert "100%" in solution.message
    assert "20.0%" in solution.message  # says by how much it failed


def test_unreachable_target_reports_the_closest_average():
    # One assessment only, so the class average is pinned at 40%: 80% is impossible.
    marks = np.array([[40.0], [40.0]])

    solution = solve_weight_ranges(
        marks, 80.0, np.array([0.5]), np.array([1.0]), names=["Only test"]
    )

    assert solution.status == "optimal"
    assert solution.target_reached is False
    assert solution.class_average == 40.0
    assert "not reachable" in solution.message
    assert "40.0 marks" in solution.message  # 80 - 40, stated explicitly


def test_maximums_that_cannot_reach_100_percent_are_infeasible():
    lower = np.array([0.01, 0.01, 0.01])
    upper = np.array([0.2, 0.2, 0.2])  # only 60% available in total

    solution = solve_weight_ranges(_marks(), 65.0, lower, upper, names=["A", "B", "C"])

    assert solution.status == "infeasible"
    assert "less than 100%" in solution.message
    assert "40.0%" in solution.message


# --------------------------------------------------------------------------- #
# Route level (/cohort)
# --------------------------------------------------------------------------- #
def test_feasible_ranges_solve_and_render_the_result():
    resp = _client().post("/cohort", data=_form())

    body = resp.data.decode("utf-8")
    assert resp.status_code == 200
    assert "status-banner" in body  # solver status is always surfaced
    assert "Proposed weight (%)" in body  # results table rendered
    assert "flash-error" not in body
    for name in DEFAULT_RANGES:
        assert name in body


def test_missing_target_field_keeps_working():
    """Regression: the POST used to require target_average and rejected every run."""
    body = _client().post("/cohort", data=_form(target=None)).data.decode("utf-8")

    assert "Invalid target average" not in body
    assert "Proposed weight (%)" in body
    assert "flash-error" not in body


def test_reachable_target_is_reported_as_reached():
    wide = {name: (5.0, 60.0) for name in DEFAULT_RANGES}

    body = _client().post(
        "/cohort", data=_form(target="45", ranges=wide)
    ).data.decode("utf-8")

    assert "Target reached" in body


def test_zero_minimum_is_rejected_on_the_page():
    ranges = dict(DEFAULT_RANGES)
    ranges["Class Test 1"] = (0.0, 25.0)

    body = _client().post("/cohort", data=_form(ranges=ranges)).data.decode("utf-8")

    assert "must be greater than 0%" in body
    assert "Proposed weight (%)" not in body  # no result table on a rejected run


def test_negative_minimum_is_rejected_on_the_page():
    ranges = dict(DEFAULT_RANGES)
    ranges["Practical"] = (-5.0, 20.0)

    body = _client().post("/cohort", data=_form(ranges=ranges)).data.decode("utf-8")

    assert "must be greater than 0%" in body
    assert "Proposed weight (%)" not in body


def test_minimum_above_maximum_is_rejected_on_the_page():
    ranges = dict(DEFAULT_RANGES)
    ranges["Assignment 1"] = (40.0, 20.0)

    body = _client().post("/cohort", data=_form(ranges=ranges)).data.decode("utf-8")

    assert "is above its maximum" in body
    assert "Proposed weight (%)" not in body


def test_minimums_adding_up_to_more_than_100_is_rejected_on_the_page():
    ranges = {name: (30.0, 60.0) for name in DEFAULT_RANGES}  # 180% of minimums

    body = _client().post("/cohort", data=_form(ranges=ranges)).data.decode("utf-8")

    assert "more than 100%" in body
    assert "80.0%" in body  # 180 - 100, stated explicitly
    assert "Proposed weight (%)" not in body


def test_maximums_adding_up_to_less_than_100_is_rejected_on_the_page():
    ranges = {name: (1.0, 5.0) for name in DEFAULT_RANGES}  # only 30% of maximums

    body = _client().post("/cohort", data=_form(ranges=ranges)).data.decode("utf-8")

    assert "less than 100%" in body
    assert "70.0%" in body  # 100 - 30, stated explicitly
    assert "Proposed weight (%)" not in body


def test_non_numeric_range_reports_a_friendly_error():
    body = _client().post(
        "/cohort",
        data=_form(**{"min_Class Test 1": "abc"}),
    ).data.decode("utf-8")

    assert "must be a number" in body
    assert "Proposed weight (%)" not in body


def test_target_must_be_a_number():
    body = _client().post("/cohort", data=_form(target="sixty")).data.decode("utf-8")

    assert "Enter the target class average as a number" in body


def test_target_out_of_range_is_rejected():
    body = _client().post("/cohort", data=_form(target="150")).data.decode("utf-8")

    assert "must be between 0% and 100%" in body
