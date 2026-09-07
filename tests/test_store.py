import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from backend.data.loader import load_dataframe
from backend.data.store import DataStore

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

    assert len(module.assessments) == 6
    assert len(module.students) == 15
    assert all(len(s.assessments) == 6 for s in module.students)
    # Completed assessments carry marks; remaining ones do not.
    stu = module.student("STU001")
    assert stu is not None
    assert stu.assessments[0].mark == 66.1
    assert stu.assessments[0].completed is True
    assert stu.assessments[3].mark is None and stu.assessments[3].completed is False
    assert round(stu.p_mark_current, 2) == round(66.1 * 0.15 + 73.9 * 0.15 + 82.7 * 0.2, 2)


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


def test_export_round_trips_through_import(store: DataStore):
    """A module serialised to the long CSV format re-imports unchanged."""
    df = load_dataframe(str(SAMPLE_CSV), filename="sample_data.csv")
    module = DataStore.build_module_from_df("CS101", "Sample", df)

    exported = DataStore.module_to_dataframe(module)
    rebuilt = DataStore.build_module_from_df("CS101", "Sample", exported)

    assert list(exported.columns) == [
        "student_code", "assessment_name", "weight", "mark", "completed"
    ]
    assert _snapshot(module) == _snapshot(rebuilt)
