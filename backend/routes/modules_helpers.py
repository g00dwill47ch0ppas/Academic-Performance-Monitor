"""CSV import helpers for the enter-marks / students pages.

These helpers parse the two CSV shapes the UI supports:

* Enter marks -> one assessment per file, columns: student_code, mark
* Add students -> whole cohort, columns: student_code, mark_0, mark_1, ...

Both helpers validate against the active module's plan so the UI can show
friendly errors before touching the store.
"""

from __future__ import annotations

import csv
import io
from typing import Any

from backend.data.loader import load_dataframe
from backend.models.student import Assessment, Student


def _build_wide_marks_df(module: Any, assessment_name: str, rows: list[tuple[str, float | None]]) -> dict[str, Any]:
    """Build a wide-format frame (student_code, assessment_name, weight, mark, completed)
    from the validated rows, reusing the module plan for weights."""
    by_code: dict[str, float | None] = {code: mark for code, mark in rows}
    records: list[dict[str, Any]] = []
    plan = module.assessment(assessment_name)
    if plan is None:
        return {"records": records}
    for code, mark in rows:
        records.append(
            {
                "student_code": code,
                "assessment_name": assessment_name,
                "weight": plan.weight,
                "mark": "" if mark is None else mark,
                "completed": mark is not None,
            }
        )
    return {"records": records}


def parse_mark_import_csv(
    module: Any, file_storage: Any, filename: str
) -> tuple[str, list[tuple[str, float | None]], str | None]:
    """Validate a per-assessment marks CSV and return (assessment_name, rows, error).

    The file must have an ``assessment_name`` column (so we know which assessment
    it is for) and a ``student_code`` / ``mark`` pair. Blank marks are treated
    as "not yet written".
    """    # Read the raw CSV with the stdlib so we can accept the compact two-column
    # shape the enter-marks UI exports (assessment_name, student_code, mark).
    stream = file_storage.stream
    stream.seek(0)
    sample = stream.read(4096)
    stream.seek(0)
    if isinstance(sample, bytes):
        text = sample.decode("utf-8-sig")
    else:
        text = sample
    rdr = csv.DictReader(io.StringIO(text))
    if rdr.fieldnames is None:
        return "", [], "The file appears to be empty."
    column_map = {fn.strip().lower(): fn for fn in rdr.fieldnames}
    name_key = column_map.get("assessment_name")
    code_key = column_map.get("student_code")
    mark_key = column_map.get("mark")
    if name_key is None or code_key is None or mark_key is None:
        missing = [c for c in ("assessment_name", "student_code", "mark") if c not in column_map]
        return "", [], f"CSV missing column(s): {', '.join(missing)}."

    rows: list[tuple[str, float | None]] = []
    name_set: set[str] = set()
    plan_names = {a.name for a in module.assessments}
    for row in rdr:
        name = str(row.get(name_key, "")).strip()
        code = str(row.get(code_key, "")).strip()
        raw = row.get(mark_key, "")
        if not code:
            continue
        name_set.add(name)
        if raw is None or raw == "":
            rows.append((code, None))
        else:
            try:
                mark = float(raw)
            except (TypeError, ValueError):
                return "", [], f"Non-numeric mark for {code}."
            if not 0 <= mark <= 100:
                return "", [], f"Mark for {code} must be between 0 and 100."
            rows.append((code, mark))

    if len(rows) == 0:
        return "", [], "The file has no valid rows."
    if not name_set.issubset(plan_names):
        unexpected = name_set - plan_names
        return "", [], f"Unknown assessment(s) in file: {', '.join(sorted(unexpected))}."
    if len(name_set) != 1:
        return "", [], "One assessment per file — the CSV contains multiple assessment names."

    return next(iter(name_set)), rows, None


def parse_student_import_csv(
    module: Any, file_storage: Any, filename: str
) -> tuple[list[dict[str, Any]], str | None]:
    """Validate a student-mark CSV and return (row_dicts, error).

    Expected columns: student_code, mark_0, mark_1, ... in the same order as
    the module's plan. Extra columns are ignored; missing columns are treated
    as blank. Duplicate student codes are flagged as one error.
    """
    stream = file_storage.stream
    stream.seek(0)
    sample = stream.read(4096)
    stream.seek(0)
    if isinstance(sample, bytes):
        text = sample.decode("utf-8-sig")
    else:
        text = sample
    rdr = csv.DictReader(io.StringIO(text))
    if rdr.fieldnames is None:
        return [], "The file appears to be empty."
    column_map = {fn.strip().lower(): fn for fn in rdr.fieldnames}
    code_key = column_map.get("student_code")
    if code_key is None:
        return [], "CSV must contain a student_code column."

    plan_names = [a.name for a in module.assessments]
    seen: dict[str, bool] = {}
    rows: list[dict[str, Any]] = []
    for row in rdr:
        code = str(row.get(code_key, "")).strip()
        if not code:
            continue
        if code in seen:
            return [], f"Duplicate student code in file: {code}."
        seen[code] = True
        marks: list[float | None] = []
        for i, _plan_name in enumerate(plan_names):
            col_key = column_map.get(f"mark_{i}")
            raw = row.get(col_key, "") if col_key is not None else ""
            if raw is None or raw == "":
                marks.append(None)
            else:
                try:
                    mark = float(raw)
                except (TypeError, ValueError):
                    return [], f"Non-numeric mark for {code} (assessment {i})."
                if not 0 <= mark <= 100:
                    return [], f"Mark for {code} (assessment {i}) must be between 0 and 100."
                marks.append(mark)
        rows.append({"code": code, "marks": marks})
    if len(rows) == 0:
        return [], "The file has no valid rows."
    return rows, None
