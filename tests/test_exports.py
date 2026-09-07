import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend import create_app


def _client():
    app = create_app()
    return app.test_client()


def test_data_export_matches_import_schema():
    resp = _client().get("/modules/CS101/export")
    assert resp.status_code == 200
    lines = resp.data.decode("utf-8").strip().splitlines()
    assert lines[0] == "student_code,assessment_name,weight,mark,completed"
    assert len(lines) == 91  # header + 15 students x 6 assessments


def test_summary_export_contains_bounds_and_at_risk():
    resp = _client().get("/modules/CS101/summary-export")
    assert resp.status_code == 200
    assert "filename=CS101_summary.csv" in resp.headers["Content-Disposition"]

    lines = resp.data.decode("utf-8").strip().splitlines()
    assert lines[0] == "student_code,current_pmark,min_pmark,max_pmark,at_risk"
    assert len(lines) == 16  # header + 15 students

    parts = lines[1].split(",")
    assert parts[0] == "STU001"
    assert parts[1:4] == ["37.54", "37.54", "87.54"]
    assert parts[4] == "False"


def test_export_unknown_module_redirects():
    resp = _client().get("/modules/NOPE123/summary-export")
    assert resp.status_code == 302
