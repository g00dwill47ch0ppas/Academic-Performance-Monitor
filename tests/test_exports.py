import io
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
    assert lines[0] == (
        "student_code,assessment_name,weight,mark,completed,group,items,"
        "count_best,item_max"
    )
    assert len(lines) == 271  # header + 15 students x 18 assessment items


def test_data_export_round_trips_through_the_import_route():
    """The exported file can be imported again and keeps the drop rule intact."""
    export = _client().get("/modules/CS101/export")
    client = _client()
    response = client.post(
        "/modules/import",
        data={
            "module_code": "CS101X",
            "module_name": "Round trip",
            "data_file": (io.BytesIO(export.data), "CS101_data.csv"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code in (200, 302)

    from backend.data.store import data_store

    rebuilt = data_store.modules["CS101X"]
    assert [(a.name, a.items, a.count_best) for a in rebuilt.assessments] == [
        ("Class Test", 3, 2),
        ("Assignment", 2, 2),
        ("Practical", 1, 1),
        ("Attendance", 12, 10),
    ]


def test_summary_export_contains_bounds_and_at_risk():
    resp = _client().get("/modules/CS101/summary-export")
    assert resp.status_code == 200
    assert "filename=CS101_summary.csv" in resp.headers["Content-Disposition"]

    lines = resp.data.decode("utf-8").strip().splitlines()
    assert lines[0] == (
        "student_code,participation_so_far,current_standing,min_pmark,max_pmark,at_risk"
    )
    assert len(lines) == 16  # header + 15 students

    parts = lines[1].split(",")
    assert parts[0] == "STU001"
    assert parts[1:5] == ["54.86", "73.14", "54.86", "86.46"]
    assert parts[5] == "False"


def test_export_unknown_module_redirects():
    resp = _client().get("/modules/NOPE123/summary-export")
    assert resp.status_code == 302
