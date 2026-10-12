"""Student detail — feasible region and target-driven projection (Task 2).

Route level, through the pages the lecturer actually uses: the region bar, a
target at both ends of the region, a mid-region target whose returned plan
recomputes to the target, an out-of-region target rejected, and the property that
every remaining item appears in the plan.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend import create_app
from backend.algorithms.participation_plan import build_projection, feasible_region
from backend.data.store import data_store
from backend.services.participation import analyse, final_with_marks

MODULE = "TSTPLAN"


@pytest.fixture()
def client():
    """A throwaway module with one droppable type, active for the duration."""
    previous = data_store.active_module_code
    module = data_store.create_module(MODULE, "Target plan fixture", pass_threshold=50)
    data_store.add_assessment(module, "Tests", 0.3, items=3, count_best=2)
    data_store.add_assessment(module, "Exam", 0.7, items=1, count_best=1)
    # 60 and 80 written; the third test and the exam are still open.
    data_store.add_student(module, "S1", [60.0, 80.0, None, None])
    data_store.add_student(module, "S2", [None, None, None, None])
    try:
        yield create_app().test_client()
    finally:
        data_store.delete_module(MODULE)
        if previous:
            data_store.activate(previous)


def _student() -> object:
    return data_store.modules[MODULE].student("S1")


def test_region_is_shown_up_front(client):
    response = client.get("/student/S1")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Feasible region" in body
    assert "Passing is no longer possible" not in body


def test_target_at_both_ends_of_the_region(client):
    region = feasible_region(_student().assessments)
    at_min = client.get(f"/student/S1?target={region.minimum}")
    at_max = client.get(f"/student/S1?target={region.maximum}")
    assert at_min.status_code == 200
    assert at_max.status_code == 200
    assert f"To reach {int(region.minimum)}%" in at_min.get_data(as_text=True)
    assert f"To reach {int(region.maximum)}%" in at_max.get_data(as_text=True)


def test_mid_region_target_recomputes_to_the_target(client):
    student = _student()
    region = feasible_region(student.assessments)
    target = (region.minimum + region.maximum) / 2
    response = client.get(f"/student/S1?target={target}")
    assert response.status_code == 200

    projection = build_projection(student.assessments, target)
    assert projection.reachable
    overrides = {item.name: projection.required_percentage for item in projection.items}
    achieved = final_with_marks(student.assessments, overrides).accrued
    assert achieved == pytest.approx(target, abs=1e-6)


def test_out_of_region_target_is_rejected(client):
    student = _student()
    region = feasible_region(student.assessments)
    response = client.get(f"/student/S1?target={region.maximum + 5}")
    body = response.get_data(as_text=True)
    assert response.status_code == 200  # rejected on the page, not a crash
    assert "feasible region" in body
    assert "Choose a target between" in body


def test_non_numeric_target_is_explained(client):
    response = client.get("/student/S1?target=soon")
    assert response.status_code == 200
    assert "Enter the target as a number" in response.get_data(as_text=True)


def test_plan_includes_every_remaining_item(client):
    student = _student()
    target = (feasible_region(student.assessments).minimum + 1) / 1
    projection = build_projection(student.assessments, target)
    remaining = [r.name for r in analyse(student.assessments).records if not r.has_mark]
    assert sorted(item.name for item in projection.items) == sorted(remaining)
    assert len(projection.items) == 2  # test 3 and the exam

    body = client.get(f"/student/S1?target={target}").get_data(as_text=True)
    for name in remaining:
        assert name in body


def test_student_with_nothing_recorded_has_the_full_region(client):
    response = client.get("/student/S2")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    student = data_store.modules[MODULE].student("S2")
    region = feasible_region(student.assessments)
    assert region.minimum == 0.0
    assert region.maximum == pytest.approx(100.0)
    assert "0" in body


def test_no_remaining_items_collapses_the_region_to_a_point(client):
    data_store.set_assessment_marks(
        data_store.modules[MODULE], "Tests 3", {"S1": 90.0}
    )
    data_store.set_assessment_marks(data_store.modules[MODULE], "Exam", {"S1": 70.0})
    student = _student()
    region = feasible_region(student.assessments)
    assert region.is_point

    body = client.get("/student/S1").get_data(as_text=True)
    assert "Nothing remains to be written" in body
    assert region.minimum == pytest.approx(region.maximum)


def test_projection_message_is_rounded_for_display(client):
    student = _student()
    projection = build_projection(student.assessments, 40.0)
    assert projection.required_percentage is not None
    # Display rounding: at most two decimals, no needless ".00".
    for token in projection.summary.split():
        if token.endswith("%") and any(ch.isdigit() for ch in token):
            decimals = token.rstrip("%").split(".")
            assert len(decimals) == 1 or len(decimals[1]) <= 2


def test_student_page_marks_dropped_items(client):
    """A third class test pushes the weakest mark out and the page says so."""
    data_store.set_assessment_marks(data_store.modules[MODULE], "Tests 3", {"S1": 50.0})
    body = client.get("/student/S1").get_data(as_text=True)
    assert "Dropped" in body
    assert "Tests 3" in body
    assert "currently dropped" in body
