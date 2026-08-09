import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.algorithms.participation_plan import generate_participation_plan
from backend.models.student import Assessment


def test_no_remaining_assessments_returns_empty():
    assessments = [Assessment(name="Test 1", weight=1.0, mark=70, completed=True)]
    result = generate_participation_plan(assessments, current_pmark=70, target_improvement_pct=10)
    assert result == []


def test_generates_scenarios_meeting_target():
    assessments = [
        Assessment(name="Test 1", weight=0.5, mark=60, completed=True),
        Assessment(name="Test 2", weight=0.5, mark=None, completed=False),
    ]
    result = generate_participation_plan(
        assessments, current_pmark=30, target_improvement_pct=10, step=10
    )
    assert len(result) > 0
    for scenario in result:
        assert scenario["resulting_pmark"] >= 33
