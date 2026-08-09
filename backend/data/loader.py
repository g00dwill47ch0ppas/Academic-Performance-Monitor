"""
Class assessment data import and validation (FR1, FR2).

Expected file columns (long format — one row per student per assessment):
student_code, assessment_name, weight, mark, completed

Supports .csv and .xlsx (openpyxl engine, matching the project's tech stack).
"""

import pandas as pd

# Column-name patterns that suggest identifiable data (FR2 / ethics requirement).
# Deliberately specific (not just "name") to avoid false positives on legitimate
# columns like "assessment_name".
DENYLIST_PATTERNS = [
    "student_name",
    "full_name",
    "first_name",
    "last_name",
    "surname",
    "id_number",
    "id number",
    "national_id",
    "email",
    "student_number",
]

REQUIRED_COLUMNS = {"student_code", "assessment_name", "weight", "mark", "completed"}


class PIIValidationError(ValueError):
    """Raised when an uploaded file appears to contain identifiable data."""


def validate_no_pii(df: pd.DataFrame) -> None:
    lowered_cols = [c.lower() for c in df.columns]
    for pattern in DENYLIST_PATTERNS:
        for col in lowered_cols:
            if pattern in col:
                raise PIIValidationError(
                    f"Column '{col}' may contain identifiable data and cannot be "
                    "loaded. Only anonymised student codes are permitted "
                    "(see Research Proposal, Ethical Considerations §1.5.2)."
                )


def _validate_schema(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"File is missing required columns: {missing}")


def load_dataframe(path_or_buffer, filename: str) -> pd.DataFrame:
    """Loads a CSV or XLSX file, validates it, and returns a clean DataFrame."""
    if filename.lower().endswith(".xlsx"):
        df = pd.read_excel(path_or_buffer, engine="openpyxl")
    else:
        df = pd.read_csv(path_or_buffer)

    validate_no_pii(df)
    _validate_schema(df)

    # Normalise "completed" to a real boolean regardless of how it was written
    # in the source file (True/False, TRUE/FALSE, 1/0).
    df["completed"] = df["completed"].astype(str).str.strip().str.lower().isin(
        ["true", "1", "yes"]
    )
    return df


def compute_current_pmarks(df: pd.DataFrame) -> pd.DataFrame:
    """FR3 — p = sum(y_i * w_i) over completed assessments, per student."""
    completed = df[df["completed"]]
    completed = completed.assign(contribution=completed["mark"] * completed["weight"])
    return (
        completed.groupby("student_code")["contribution"]
        .sum()
        .reset_index()
        .rename(columns={"contribution": "p_mark_current"})
    )
