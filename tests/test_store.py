import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from backend.data.loader import load_dataframe
from backend.data.store import DataStore
from backend.services.participation import analyse

SAMPLE_CSV = Path(__file__).parent.parent / "backend" / "data" / "sample_data.csv"


@pytest.fixture()
def store() -> DataStore:
    return DataStore()


def test_create_module_activates_and_rejects_duplicates(store: DataStore):
    module = store.create_module("MTHS111", "Calculus 1")
    assert module.code == "MTHS111"
    assert module.name == "Calculus 1"
    assert store.active_module is module
    assert store.active_module.label == "MTHS111 — Calculus 1"

    with pytest.raises(ValueError):
        store.create_module("MTHS111")
    with pytest.raises(ValueError):
        store.create_module("   ")


def test_rename_module_updates_active_key(store: DataStore):
    store.create_module("MTHS111", "Calculus 1")
    store.rename_module("MTHS111", "MTHS121", "Calculus 1B")
    assert "MTHS111" not in store.modules
    assert store.modules["MTHS121"].label == "MTHS121 — Calculus 1B"
    assert store.active_module_code == "MTHS121"


def test_plan_edits_stay_in_sync_with_students(store: DataStore):
    module = store.create_module("MTHS111")
    store.add_assessment(module, "Test 1", 0.5)
    store.add_assessment(module, "Test 2", 0.5)

    store.add_student(module, "STU001", [60.0, None])
    assert store.add_student(module, "STU002", [80.0, 90.0]).student_code == "STU002"

    # Weight change propagates to every student record.
    store.update_assessment(module, "Test 1", 0.6)
    assert module.assessment("Test 1").weight == 0.6
    for student in module.students:
        assert module.student_assessment(student, "Test 1").weight == 0.6

    # Removing an assessment removes it everywhere.
    store.delete_assessment(module, "Test 2")
    assert [a.name for a in module.assessments] == ["Test 1"]
    assert all(len(s.assessments) == 1 for s in module.students)

    # Adding an assessment back gives every student a blank 'remaining' entry.
    store.add_assessment(module, "Practical", 0.4)
    for student in module.students:
        entry = module.student_assessment(student, "Practical")
        assert entry is not None and entry.mark is None and not entry.completed


def test_student_add_update_delete(store: DataStore):
    module = store.create_module("MTHS111")
    store.add_assessment(module, "Test", 1.0)
    store.add_student(module, "STU001", [72.5])
    student = module.student("STU001")
    assert student.p_mark_current == 72.5
    assert student.assessments[0].completed is True

    # Blank mark means not completed.
    store.add_student(module, "STU002", [None])
    assert module.student("STU002").p_mark_current == 0.0

    with pytest.raises(ValueError):
        store.add_student(module, "STU001")

    # Editing marks + renaming the code.
    store.update_student(module, "STU001", "STU010", [None])
    assert module.student("STU010") is not None
    assert module.student("STU010").assessments[0].completed is False
    assert module.student("STU001") is None

    with pytest.raises(ValueError):
        store.update_student(module, "STU010", "STU002", [50.0])

    store.delete_student(module, "STU010")
    assert len(module.students) == 1


def test_build_module_from_sample_csv(store: DataStore):
    df = load_dataframe(str(SAMPLE_CSV), filename="sample_data.csv")
    module = DataStore.build_module_from_df("CS101", "Sample", df)

    # Four assessment types, nine items: two of the types drop marks.
    assert [a.name for a in module.assessments] == [
        "Class Test",
        "Assignment",
        "Practical",
        "Attendance",
    ]
    assert [(a.items, a.count_best) for a in module.assessments] == [
        (3, 2),
        (2, 2),
        (1, 1),
        (12, 10),
    ]
    assert len(module.plan_items()) == 18
    assert len(module.students) == 15
    assert all(len(s.assessments) == 18 for s in module.students)

    # The best 2 of the 3 class tests count, so the third mark is dropped.
    stu = module.student("STU001")
    assert stu is not None
    assert stu.assessments[0].mark == 66.1
    assert stu.assessments[0].completed is True
    counts = analyse(stu.assessments)
    class_tests = [r for r in counts.records if r.type_name == "Class Test"]
    assert len(class_tests) == 3
    assert sum(1 for r in class_tests if r.dropped) == 1


def _snapshot(module):
    """Tuple view of a module used to compare full contents."""
    return {
        (s.student_code, a.name): (a.mark, a.completed)
        for s in module.students
        for a in s.assessments
    }, tuple(a.name for a in module.assessments), tuple(
        a.weight for a in module.assessments
    )


def test_set_assessment_marks_bulk(store: DataStore):
    module = store.create_module("MTHS111")
    store.add_assessment(module, "Test 1", 0.5)
    store.add_assessment(module, "Test 2", 0.5)
    store.add_student(module, "STU001", [60.0, 50.0])
    store.add_student(module, "STU002", [None, None])

    store.set_assessment_marks(module, "Test 1", {"STU001": 90.0, "STU002": None})

    stu1 = module.student("STU001")
    stu2 = module.student("STU002")
    assert module.student_assessment(stu1, "Test 1").mark == 90.0
    assert module.student_assessment(stu1, "Test 1").completed is True
    # STU002's Test 1 was blanked -> now 'not yet written'.
    assert module.student_assessment(stu2, "Test 1").mark is None
    assert module.student_assessment(stu2, "Test 1").completed is False
    # Test 2 untouched, other plans/weights unchanged.
    assert module.student_assessment(stu1, "Test 2").mark == 50.0
    assert module.assessment("Test 1").weight == 0.5

    with pytest.raises(ValueError):
        store.set_assessment_marks(module, "Nope", {"STU001": 1.0})


def test_set_assessment_marks_bulk_allows_blanking(store: DataStore):
    module = store.create_module("MTHS111")
    store.add_assessment(module, "Test 1", 0.5)
    store.add_assessment(module, "Test 2", 0.5)
    store.add_student(module, "STU001", [60.0])

    store.set_assessment_marks(module, "Test 1", {"STU001": None})
    assert module.student_assessment(module.student("STU001"), "Test 1").mark is None
    assert module.student_assessment(module.student("STU001"), "Test 1").completed is False


def test_build_module_from_sample_csv(store: DataStore):
    """A module serialised to the long CSV format re-imports unchanged."""
    df = load_dataframe(str(SAMPLE_CSV), filename="sample_data.csv")
    module = DataStore.build_module_from_df("CS101", "Sample", df)

    exported = DataStore.module_to_dataframe(module)
    rebuilt = DataStore.build_module_from_df("CS101", "Sample", exported)

def test_student_import_csv_shape(store: DataStore):
    from backend.routes.modules_helpers import parse_student_import_csv

    module = store.create_module("MTHS111")
    store.add_assessment(module, "Test 1", 0.5)
    store.add_assessment(module, "Test 2", 0.5)

    import io

    class _fs:
        def __init__(self, stream, filename):
            self.stream = stream
            self.filename = filename

    payload = (
        "student_code,mark_0,mark_1\n"
        "STU010,60,70\n"
        "STU011,,80\n"
    )
    parsed, error = parse_student_import_csv(
        module, _fs(io.BytesIO(payload.encode()), "import.csv"), "import.csv"
    )
    assert error is None
    assert len(parsed) == 2
    assert parsed[0]["code"] == "STU010"
    assert parsed[0]["marks"] == [60.0, 70.0]
    assert parsed[1]["code"] == "STU011"
    assert parsed[1]["marks"] == [None, 80.0]


def test_mark_import_csv_shape(store: DataStore):
    from backend.routes.modules_helpers import parse_mark_import_csv

    module = store.create_module("MTHS111")
    store.add_assessment(module, "Test 1", 0.5)
    store.add_assessment(module, "Test 2", 0.5)

    import io

    class _fs:
        def __init__(self, stream, filename):
            self.stream = stream
            self.filename = filename

    payload = (
        "assessment_name,student_code,mark\n"
        "Test 1,STU001,60\n"
        "Test 1,STU002,\n"
    )
    name, rows, error = parse_mark_import_csv(
        module,
        _fs(io.BytesIO(payload.encode()), "marks.csv"),
        "marks.csv",
    )
    assert error is None, error
    assert name == "Test 1"
    assert len(rows) == 2
    assert rows[0][1] == 60.0
    assert rows[1][1] is None


def test_student_import_csv_shape(store: DataStore):
    from backend.routes.modules_helpers import parse_student_import_csv

    module = store.create_module("MTHS111")
    store.add_assessment(module, "Test 1", 0.5)
    store.add_assessment(module, "Test 2", 0.5)

    import io

    class _fs:
        def __init__(self, stream, filename):
            self.stream = stream
            self.filename = filename

    payload = (
        "student_code,mark_0,mark_1\n"
        "STU010,60,70\n"
        "STU011,,80\n"
    )
    parsed, error = parse_student_import_csv(
        module, _fs(io.BytesIO(payload.encode()), "import.csv"), "import.csv"
    )
    assert error is None, error
    assert len(parsed) == 2
    assert parsed[0]["code"] == "STU010"
    assert parsed[0]["marks"] == [60.0, 70.0]
    assert parsed[1]["code"] == "STU011"
    assert parsed[1]["marks"] == [None, 80.0]


def test_export_round_trips_through_import(store: DataStore):
    exported = DataStore.module_to_dataframe(store.create_module("CS101", "Sample"))
    rebuilt = DataStore.build_module_from_df("CS101", "Sample", exported)

    assert list(exported.columns) == [
        "student_code",
        "assessment_name",
        "weight",
        "mark",
        "completed",
        "group",
        "items",
        "count_best",
        "item_max",
    ]
    assert _snapshot(store.modules["CS101"]) == _snapshot(rebuilt)


def test_export_round_trips_the_drop_rule(store: DataStore):
    """Items, count-best and weights survive a full export/import round trip."""
    module = store.create_module("MTHS111", "Algebra")
    store.add_assessment(module, "Tests", 0.6, items=3, count_best=2)
    store.add_assessment(module, "Attendance", 0.4, items=4, count_best=3)
    store.add_student(module, "STU001", [60.0, 80.0, 50.0, 100.0, 100.0, 0.0, None])

    exported = DataStore.module_to_dataframe(module)
    rebuilt = DataStore.build_module_from_df("MTHS111", "Algebra", exported)

    assert [(a.name, a.items, a.count_best) for a in rebuilt.assessments] == [
        ("Tests", 3, 2),
        ("Attendance", 4, 3),
    ]
    original = analyse(module.student("STU001").assessments)
    round_tripped = analyse(rebuilt.student("STU001").assessments)
    assert round_tripped.accrued == pytest.approx(original.accrued)
    assert round_tripped.standing == pytest.approx(original.standing)
