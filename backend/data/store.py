"""
In-memory data store for the currently loaded class dataset.

This is a deliberate simplification appropriate to the artefact's scope (a
single-lecturer research prototype used in one evaluation session at a time,
per Research Proposal §1.4.6 — not a multi-tenant production system). Data
lives only in server memory for the lifetime of the process, satisfying the
project's ethics requirement of never persisting identifiable data (NFR3).
"""

import pandas as pd

from backend.data.loader import load_dataframe
from backend.models.student import Assessment, ClassConfig, Student


class DataStore:
    def __init__(self):
        self.df: pd.DataFrame | None = None
        self.config = ClassConfig()

    def load_from_csv(self, path: str) -> None:
        self.df = load_dataframe(path, filename=path)

    def load_from_upload(self, file_storage) -> None:
        self.df = load_dataframe(file_storage.stream, filename=file_storage.filename)

    def student_codes(self) -> list[str]:
        if self.df is None:
            return []
        return sorted(self.df["student_code"].unique())

    def get_student(self, student_code: str) -> Student:
        rows = self.df[self.df["student_code"] == student_code]
        assessments = [
            Assessment(
                name=row["assessment_name"],
                weight=float(row["weight"]),
                mark=float(row["mark"]) if row["completed"] and str(row["mark"]) != "" else None,
                completed=bool(row["completed"]),
            )
            for _, row in rows.iterrows()
        ]
        return Student(student_code=student_code, assessments=assessments)

    def all_students(self) -> list[Student]:
        return [self.get_student(code) for code in self.student_codes()]


# Single shared instance — see module docstring for the scope this is intended for.
data_store = DataStore()
