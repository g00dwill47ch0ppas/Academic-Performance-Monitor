import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.algorithms.lp_bounds import compute_pmark_bounds, is_at_risk
from backend.models.student import Assessment


def test_all_completed_gives_fixed_pmark():
    assessments = [
        Assessment(name="Test 1", weight=0.5, mark=80, completed=True),
        Assessment(name="Test 2", weight=0.5, mark=60, completed=True),
    ]
    min_pm, max_pm = compute_pmark_bounds(assessments)
    assert min_pm == max_pm == 70.0


def test_remaining_assessment_widens_bounds():
    assessments = [
        Assessment(name="Test 1", weight=0.5, mark=80, completed=True),
        Assessment(name="Test 2", weight=0.5, mark=None, completed=False),
    ]
    min_pm, max_pm = compute_pmark_bounds(assessments)
    assert min_pm == 40.0
    assert max_pm == 90.0


def test_is_at_risk_flags_below_threshold():
    assert is_at_risk(max_pmark=45.0, pass_threshold=50.0) is True
    assert is_at_risk(max_pmark=55.0, pass_threshold=50.0) is False
