"""
In-memory data store for modules, their assessment plans, and their students.

This is a deliberate simplification appropriate to the artefact's scope (a
single-lecturer research prototype used in one evaluation session at a time,
per Research Proposal §1.4.6 — not a multi-tenant production system). Data
lives only in server memory for the lifetime of the process, satisfying the
project's ethics requirement of never persisting identifiable data (NFR3).

A lecturer creates modules (e.g. "MTHS111 — Calculus 1"); each module owns an
assessment plan (names + weights) and a set of anonymised students with marks
on that plan. Exactly one module is "active" at a time and the analytical
pages (dashboard, at-risk, cohort planning, ...) operate on that module.
"""

import pandas as pd

from backend.data.loader import load_dataframe
from backend.models.student import Assessment, ClassConfig, Module, Student
from config import Config


class DataStore:
    def __init__(self):
        self.modules: dict[str, Module] = {}
        self.active_module_code: str | None = None

    # ------------------------------------------------------------------ #
    # Module-level accessors
    # ------------------------------------------------------------------ #
    @property
    def active_module(self) -> Module | None:
        if self.active_module_code is None:
            return None
        return self.modules.get(self.active_module_code)

    def module_list(self) -> list[Module]:
        """All modules, sorted by code."""
        return [self.modules[code] for code in sorted(self.modules)]

    # ------------------------------------------------------------------ #
    # Module lifecycle
    # ------------------------------------------------------------------ #
    def create_module(self, code: str, name: str = "", activate: bool = True) -> Module:
        """Create a module. Raises ValueError on empty/duplicate codes."""
        code = code.strip()
        if not code:
            raise ValueError("Module code cannot be empty.")
        if code in self.modules:
            raise ValueError(f"A module with code '{code}' already exists.")
        module = Module(
            code=code,
            name=name.strip(),
            config=ClassConfig(
                pass_threshold=Config.DEFAULT_PASS_THRESHOLD,
                target_class_average=Config.DEFAULT_TARGET_CLASS_AVERAGE,
            ),
        )
        self.modules[code] = module
        if activate or self.active_module is None:
            self.active_module_code = code
        return module

    def rename_module(self, old_code: str, new_code: str, name: str = "") -> Module:
        """Rename a module (code and/or display name). Raises ValueError on conflicts."""
        module = self.modules[old_code]
        new_code = new_code.strip()
        if not new_code:
            raise ValueError("Module code cannot be empty.")
        if new_code != old_code and new_code in self.modules:
            raise ValueError(f"A module with code '{new_code}' already exists.")

        module.code = new_code
        module.name = name.strip()
        if new_code != old_code:
            del self.modules[old_code]
            self.modules[new_code] = module
            if self.active_module_code == old_code:
                self.active_module_code = new_code
        return module

    def delete_module(self, code: str) -> None:
        """Delete a module and (if it was active) make another one active."""
        if code not in self.modules:
            return
        del self.modules[code]
        if self.active_module_code == code:
            self.active_module_code = next(iter(sorted(self.modules)), None)

    def activate(self, code: str) -> bool:
        if code not in self.modules:
            return False
        self.active_module_code = code
        return True

    # ------------------------------------------------------------------ #
    # Assessment plan
    # ------------------------------------------------------------------ #
    def add_assessment(self, module: Module, name: str, weight: float) -> None:
        """Add an assessment to the plan; every student starts it as 'remaining'.

        Raises ValueError on empty/duplicate names or weights outside (0, 1].
        """
        name = name.strip()
        if not name:
            raise ValueError("Assessment name cannot be empty.")
        if module.assessment(name) is not None:
            raise ValueError(f"An assessment named '{name}' already exists.")
        if not 0 < weight <= 1:
            raise ValueError("Weight must be between 0% and 100%.")

        module.assessments.append(Assessment(name=name, weight=weight, mark=None, completed=False))
        for student in module.students:
            student.assessments.append(
                Assessment(name=name, weight=weight, mark=None, completed=False)
            )

    def update_assessment(self, module: Module, name: str, weight: float) -> None:
        """Change a plan weight; kept in sync on every student's record."""
        if not 0 < weight <= 1:
            raise ValueError("Weight must be between 0% and 100%.")
        plan_entry = module.assessment(name)
        if plan_entry is None:
            raise ValueError(f"No assessment named '{name}'.")
        plan_entry.weight = weight
        for student in module.students:
            entry = module.student_assessment(student, name)
            if entry is not None:
                entry.weight = weight

    def delete_assessment(self, module: Module, name: str) -> None:
        """Remove an assessment from the plan and from every student."""
        module.assessments = [a for a in module.assessments if a.name != name]
        for student in module.students:
            student.assessments = [a for a in student.assessments if a.name != name]

    # ------------------------------------------------------------------ #
    # Students
    # ------------------------------------------------------------------ #
    def add_student(self, module: Module, code: str, marks: list[float | None] | None = None) -> Student:
        """Enrol a new student with the module's plan. Raises ValueError on dupes.

        ``marks`` (optional) aligns with ``module.assessments`` order; a value
        of None means the assessment has not been completed yet.
        """
        code = code.strip()
        if not code:
            raise ValueError("Student code cannot be empty.")
        if module.student(code) is not None:
            raise ValueError(f"A student with code '{code}' is already enrolled.")

        if marks is None:
            marks = [None] * len(module.assessments)

        assessments = [
            Assessment(
                name=plan.name,
                weight=plan.weight,
                mark=mark,
                completed=mark is not None,
            )
            for plan, mark in zip(module.assessments, marks)
        ]
        student = Student(student_code=code, assessments=assessments)
        module.students.append(student)
        return student

    def update_student(
        self,
        module: Module,
        current_code: str,
        new_code: str,
        marks: list[float | None],
    ) -> Student:
        """Update a student's code and per-assessment marks.

        ``marks`` aligns with ``module.assessments`` order; None = not completed.
        Raises ValueError if new_code collides with another student.
        """
        student = module.student(current_code)
        if student is None:
            raise ValueError(f"No student with code '{current_code}' is enrolled.")

        new_code = new_code.strip()
        if not new_code:
            raise ValueError("Student code cannot be empty.")
        other = module.student(new_code)
        if other is not None and other is not student:
            raise ValueError(f"A student with code '{new_code}' is already enrolled.")

        student.student_code = new_code
        by_name = {a.name: a for a in student.assessments}
        for plan, mark in zip(module.assessments, marks):
            entry = by_name.get(plan.name)
            if entry is None:
                continue
            entry.mark = mark
            entry.completed = mark is not None
        return student

    def delete_student(self, module: Module, code: str) -> None:
        module.students = [s for s in module.students if s.student_code != code]

    def set_assessment_marks(
        self, module: Module, name: str, marks: dict[str, float | None]
    ) -> None:
        """Bulk-update one assessment's marks across the module's students.

        ``marks`` maps student codes to their mark (None = not completed).
        Raises ValueError if the assessment isn't in the plan.
        """
        if module.assessment(name) is None:
            raise ValueError(f"No assessment named '{name}' in this module's plan.")
        for student in module.students:
            if student.student_code not in marks:
                continue
            entry = module.student_assessment(student, name)
            if entry is None:
                continue
            mark = marks[student.student_code]
            entry.mark = mark
            entry.completed = mark is not None

    # ------------------------------------------------------------------ #
    # Bulk import (CSV/XLSX) — shared by startup seeding and module import
    # ------------------------------------------------------------------ #
    @staticmethod
    def build_module_from_df(code: str, name: str, df: pd.DataFrame) -> Module:
        """Convert a long-format assessment frame into a populated Module.

        Expected columns (see loader): student_code, assessment_name, weight,
        mark, completed. Plan weights come from the first occurrence of each
        assessment; student marks are matched back onto that plan.
        """
        code = code.strip()
        if not code:
            raise ValueError("Module code cannot be empty.")

        plan_names: list[str] = []
        plan_weights: dict[str, float] = {}
        for _, row in df.iterrows():
            an = row["assessment_name"]
            if an not in plan_weights:
                plan_names.append(an)
                plan_weights[an] = float(row["weight"])

        last_row = df.groupby(["student_code", "assessment_name"], as_index=False).tail(1)
        rows_by_student: dict[str, dict[str, tuple[float | None, bool]]] = {}
        for _, row in last_row.iterrows():
            rows_by_student.setdefault(row["student_code"], {})[row["assessment_name"]] = (
                None if pd.isna(row["mark"]) or str(row["mark"]).strip() == "" else float(row["mark"]),
                bool(row["completed"]),
            )

        students: list[Student] = []
        for s_code in sorted(rows_by_student):
            records = rows_by_student[s_code]
            assessments = []
            for an in plan_names:
                if an in records:
                    mark, completed = records[an]
                    assessments.append(
                        Assessment(name=an, weight=plan_weights[an], mark=mark, completed=completed)
                    )
                else:
                    assessments.append(
                        Assessment(name=an, weight=plan_weights[an], mark=None, completed=False)
                    )
            students.append(Student(student_code=s_code, assessments=assessments))

        module = Module(
            code=code,
            name=name.strip(),
            assessments=[
                Assessment(name=an, weight=plan_weights[an], mark=None, completed=False)
                for an in plan_names
            ],
            students=students,
            config=ClassConfig(
                pass_threshold=Config.DEFAULT_PASS_THRESHOLD,
                target_class_average=Config.DEFAULT_TARGET_CLASS_AVERAGE,
            ),
        )
        return module

    def create_module_from_file(
        self, code: str, name: str, file_storage, filename: str
    ) -> Module:
        """Create a new module from an uploaded long-format file (CSV/XLSX)."""
        df = load_dataframe(file_storage.stream, filename=filename)
        module = self.build_module_from_df(code, name, df)
        code = module.code
        if code in self.modules:
            raise ValueError(f"A module with code '{code}' already exists.")
        self.modules[code] = module
        self.active_module_code = code
        return module

    def replace_module_from_file(self, module: Module, file_storage, filename: str) -> None:
        """Overwrite an existing module's plan and students from an uploaded file.

        Keeps the module code, name and config (thresholds) intact.
        """
        df = load_dataframe(file_storage.stream, filename=filename)
        replacement = self.build_module_from_df(module.code, module.name, df)
        module.assessments = replacement.assessments
        module.students = replacement.students

    # ------------------------------------------------------------------ #
    # Bulk export
    # ------------------------------------------------------------------ #
    @staticmethod
    def module_to_dataframe(module: Module) -> pd.DataFrame:
        """Serialise a module back to the long-format frame the loader expects.

        One row per student per plan assessment: student_code, assessment_name,
        weight, mark, completed. Blank marks are empty strings so an exported
        file can be imported again unchanged (round-trip).
        """
        records = []
        for student in module.students:
            by_name = {a.name: a for a in student.assessments}
            for plan in module.assessments:
                entry = by_name.get(plan.name)
                records.append(
                    {
                        "student_code": student.student_code,
                        "assessment_name": plan.name,
                        "weight": plan.weight,
                        "mark": entry.mark if entry is not None and entry.mark is not None else "",
                        "completed": bool(entry.completed) if entry is not None else False,
                    }
                )
        return pd.DataFrame(
            records, columns=["student_code", "assessment_name", "weight", "mark", "completed"]
        )


# Single shared instance — see module docstring for the scope this is intended for.
data_store = DataStore()
