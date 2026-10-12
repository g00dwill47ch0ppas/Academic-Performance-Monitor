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
    def create_module(
        self,
        code: str,
        name: str = "",
        activate: bool = True,
        pass_threshold: float | None = None,
    ) -> Module:
        """Create a module. Raises ValueError on empty/duplicate codes or a bad threshold.

        ``pass_threshold`` (percent) is optional and falls back to the configured
        default; it can also be changed later from the Settings page.
        """
        code = code.strip()
        if not code:
            raise ValueError("Module code cannot be empty.")
        if code in self.modules:
            raise ValueError(f"A module with code '{code}' already exists.")
        threshold = (
            Config.DEFAULT_PASS_THRESHOLD
            if pass_threshold is None
            else float(pass_threshold)
        )
        if not 0 <= threshold <= 100:
            raise ValueError("Pass threshold must be between 0% and 100%.")
        module = Module(
            code=code,
            name=name.strip(),
            config=ClassConfig(
                pass_threshold=threshold,
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
    # Assessment plan (types of M items, best N of which count)
    # ------------------------------------------------------------------ #
    @staticmethod
    def validate_type(items: int, count_best: int) -> tuple[int, int]:
        """Check the droppable-assessment pair: 1 <= N <= M. Returns (M, N)."""
        try:
            items = int(items)
            count_best = int(count_best)
        except (TypeError, ValueError):
            raise ValueError(
                "Number of items and count-best must be whole numbers."
            ) from None
        if items < 1:
            raise ValueError("An assessment type needs at least 1 item.")
        if count_best < 1:
            raise ValueError("At least 1 item must count towards the participation mark.")
        if count_best > items:
            raise ValueError(
                f"Count-best ({count_best}) cannot be more than the number of "
                f"items ({items}) — only {items} can ever be written."
            )
        return items, count_best

    @staticmethod
    def _apply_item_specs(students: list[Student], specs: list[dict]) -> None:
        """Rebuild every student's item list from the plan, keeping known marks.

        Marks are matched by item name, so editing a type's item count, weight or
        count-best never loses a recorded mark.
        """
        for student in students:
            by_name = {a.name: a for a in student.assessments}
            rebuilt: list[Assessment] = []
            for spec in specs:
                existing = by_name.get(spec["name"])
                rebuilt.append(
                    Assessment(
                        name=spec["name"],
                        weight=spec["weight"],
                        mark=existing.mark if existing is not None else None,
                        completed=existing.completed if existing is not None else False,
                        group=spec["group"],
                        items=spec["items"],
                        count_best=spec["count_best"],
                        item_max=spec["item_max"],
                    )
                )
            student.assessments = rebuilt

    def _sync_plan(self, module: Module) -> None:
        """Push the plan's shape (weights, M, N, item names) onto all students."""
        specs = module.plan_item_specs()
        names = [spec["name"] for spec in specs]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ValueError(
                "Item names would clash: "
                + ", ".join(sorted(duplicates))
                + ". Rename one of the assessment types."
            )
        self._apply_item_specs(module.students, specs)

    def add_assessment(
        self,
        module: Module,
        name: str,
        weight: float,
        items: int = 1,
        count_best: int | None = None,
    ) -> None:
        """Add an assessment TYPE to the plan; students get its M blank items.

        ``items`` is M and ``count_best`` is N (the best N of M count). N defaults
        to M, which drops nothing — the behaviour that existed before this rule.
        Raises ValueError on empty/duplicate names, weights outside (0, 1] or an
        invalid (M, N) pair.
        """
        name = name.strip()
        if not name:
            raise ValueError("Assessment name cannot be empty.")
        if module.assessment(name) is not None:
            raise ValueError(f"An assessment named '{name}' already exists.")
        if not 0 < weight <= 1:
            raise ValueError("Weight must be between 0% and 100%.")
        items, count_best = self.validate_type(items, items if count_best is None else count_best)

        module.assessments.append(
            Assessment(
                name=name,
                weight=weight,
                mark=None,
                completed=False,
                group=name,
                items=items,
                count_best=count_best,
            )
        )
        self._sync_plan(module)

    def update_assessment(
        self,
        module: Module,
        name: str,
        weight: float,
        items: int | None = None,
        count_best: int | None = None,
    ) -> None:
        """Change a type's weight and/or its best-N-of-M setting.

        The plan entry and every student's items are kept in sync; marks survive
        an item-count change because items are matched by name.
        """
        if not 0 < weight <= 1:
            raise ValueError("Weight must be between 0% and 100%.")
        plan_entry = module.assessment(name)
        if plan_entry is None:
            raise ValueError(f"No assessment named '{name}'.")

        new_items = plan_entry.items if items is None else items
        new_count = plan_entry.count_best if count_best is None else count_best
        new_items, new_count = self.validate_type(new_items, new_count)

        plan_entry.weight = weight
        plan_entry.items = new_items
        plan_entry.count_best = new_count
        plan_entry.group = plan_entry.name
        self._sync_plan(module)

    def delete_assessment(self, module: Module, name: str) -> None:
        """Remove an assessment TYPE (all of its items) from every student."""
        module.assessments = [a for a in module.assessments if a.name != name]
        self._sync_plan(module)

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

        plan_items = module.plan_items()
        if marks is None:
            marks = [None] * len(plan_items)

        assessments = [
            Assessment(
                name=plan.name,
                weight=plan.weight,
                mark=mark,
                completed=mark is not None,
                group=plan.group,
                items=plan.items,
                count_best=plan.count_best,
                item_max=plan.item_max,
            )
            for plan, mark in zip(plan_items, marks)
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
        for plan, mark in zip(module.plan_items(), marks):
            entry = by_name.get(plan.name)
            if entry is None:
                continue
            entry.mark = mark
            entry.completed = mark is not None
            entry.weight = plan.weight
            entry.group = plan.group
            entry.items = plan.items
            entry.count_best = plan.count_best
            entry.item_max = plan.item_max
        return student

    def delete_student(self, module: Module, code: str) -> None:
        module.students = [s for s in module.students if s.student_code != code]

    def set_assessment_marks(
        self, module: Module, name: str, marks: dict[str, float | None]
    ) -> None:
        """Bulk-update one assessment ITEM's marks across the module's students.

        ``marks`` maps student codes to their mark (None = not completed).
        Raises ValueError if the item isn't part of the plan.
        """
        if module.plan_item(name) is None:
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

        Required columns (see loader): student_code, assessment_name, weight, mark,
        completed. Optional columns describe droppable assessment types: ``group``
        (the type an item belongs to), ``items`` (M) and ``count_best`` (N).

        A file without those columns behaves exactly as before: every assessment
        is its own type with M = N = 1. Items are matched to a type positionally,
        in first-appearance order, and take the canonical names the plan generates
        (``"<Type> 1".."<Type> M"``).
        """
        code = code.strip()
        if not code:
            raise ValueError("Module code cannot be empty.")

        def _clean(value) -> str:
            if value is None or (isinstance(value, float) and pd.isna(value)):
                return ""
            return str(value).strip()

        def _int(value) -> int | None:
            text = _clean(value)
            if text == "":
                return None
            try:
                return int(float(text))
            except (TypeError, ValueError):
                return None

        has_group = "group" in df.columns
        has_items = "items" in df.columns
        has_count_best = "count_best" in df.columns
        has_item_max = "item_max" in df.columns

        def _float(value, default: float) -> float:
            text = _clean(value)
            if text == "":
                return default
            try:
                return float(text)
            except (TypeError, ValueError):
                return default

        type_order: list[str] = []
        type_meta: dict[str, dict] = {}
        for _, row in df.iterrows():
            an = str(row["assessment_name"]).strip()
            if not an:
                continue
            group = _clean(row.get("group")) if has_group else ""
            type_name = group or an
            if type_name not in type_meta:
                type_order.append(type_name)
                type_meta[type_name] = {
                    "weight": float(row["weight"]),
                    "declared_items": _int(row.get("items")) if has_items else None,
                    "declared_count": _int(row.get("count_best")) if has_count_best else None,
                    "item_max": _float(row.get("item_max"), 100.0) if has_item_max else 100.0,
                    "item_names": [],
                }
            meta = type_meta[type_name]
            if an not in meta["item_names"]:
                meta["item_names"].append(an)

        last_row = df.groupby(["student_code", "assessment_name"], as_index=False).tail(1)
        rows_by_student: dict[str, dict[str, tuple[float | None, bool]]] = {}
        for _, row in last_row.iterrows():
            rows_by_student.setdefault(row["student_code"], {})[str(row["assessment_name"]).strip()] = (
                None if pd.isna(row["mark"]) or _clean(row["mark"]) == "" else float(row["mark"]),
                bool(row["completed"]),
            )

        plan_types: list[Assessment] = []
        for type_name in type_order:
            meta = type_meta[type_name]
            items = max(1, meta["declared_items"] or 0, len(meta["item_names"]))
            count_best = meta["declared_count"] if meta["declared_count"] else items
            count_best = max(1, min(count_best, items))
            plan_types.append(
                Assessment(
                    name=type_name,
                    weight=meta["weight"],
                    mark=None,
                    completed=False,
                    group=type_name,
                    items=items,
                    count_best=count_best,
                    item_max=meta["item_max"],
                )
            )

        module = Module(
            code=code,
            name=name.strip(),
            assessments=plan_types,
            students=[],
            config=ClassConfig(
                pass_threshold=Config.DEFAULT_PASS_THRESHOLD,
                target_class_average=Config.DEFAULT_TARGET_CLASS_AVERAGE,
            ),
        )

        specs = module.plan_item_specs()
        source_names: dict[str, list[str]] = {
            type_name: meta["item_names"] for type_name, meta in type_meta.items()
        }
        # (type, item) -> position within the type, so the file's own item labels
        # can be matched positionally onto the canonical names the plan generates.
        position_of: dict[tuple[str, str], int] = {}
        seen_per_type: dict[str, int] = {}
        for spec in specs:
            key = (spec["group"], spec["name"])
            position_of[key] = seen_per_type.get(spec["group"], 0)
            seen_per_type[spec["group"]] = position_of[key] + 1
        for s_code in sorted(rows_by_student):
            records = rows_by_student[s_code]
            assessments: list[Assessment] = []
            for spec in specs:
                source = source_names.get(spec["group"], [])
                position = position_of[(spec["group"], spec["name"])]
                original = source[position] if position < len(source) else spec["name"]
                mark, completed = records.get(original, (None, False))
                assessments.append(
                    Assessment(
                        name=spec["name"],
                        weight=spec["weight"],
                        mark=mark,
                        completed=completed,
                        group=spec["group"],
                        items=spec["items"],
                        count_best=spec["count_best"],
                        item_max=spec["item_max"],
                    )
                )
            module.students.append(Student(student_code=s_code, assessments=assessments))

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

        One row per student per plan ITEM: student_code, assessment_name, weight,
        mark, completed, plus the droppable-type columns group / items /
        count_best. Blank marks are empty strings so an exported file can be
        imported again unchanged (round-trip).
        """
        columns = [
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
        records = []
        for student in module.students:
            for entry in student.assessments:
                records.append(
                    {
                        "student_code": student.student_code,
                        "assessment_name": entry.name,
                        "weight": entry.weight,
                        "mark": entry.mark if entry.mark is not None else "",
                        "completed": bool(entry.completed),
                        "group": entry.group or entry.name,
                        "items": entry.items,
                        "count_best": entry.count_best,
                        "item_max": entry.item_max,
                    }
                )
        return pd.DataFrame(records, columns=columns)


# Single shared instance — see module docstring for the scope this is intended for.
data_store = DataStore()
