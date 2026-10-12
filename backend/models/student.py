"""
Core data model for the DSS artefact.

An Assessment represents one formative-assessment component for one student
(class test, assignment, practical, attendance, etc.). A Student is the set of
assessments for one anonymised student code. ClassConfig holds lecturer-adjustable
settings that affect the algorithms (pass threshold, target class average).

A Module is the top-level unit a lecturer manages: a module code/name, its
assessment plan (the assessments that make up the module, each with a weight),
and the students enrolled in it with their marks on that plan. Every module
carries its own ClassConfig so thresholds can differ between modules.
"""

from dataclasses import dataclass, field


@dataclass
class Assessment:
    """One assessment ITEM (a single test, attendance session, ...).

    ``weight`` is the weight of the whole assessment TYPE it belongs to, and
    ``items`` / ``count_best`` (M / N) describe that type: the best N of its M
    items count. An item that is its own type keeps the defaults M = N = 1, which
    is exactly the pre-drop behaviour (``backend/services/participation.py``).
    """
    name: str
    weight: float           # W of the type, expected in (0, 1]
    mark: float | None      # y_i, None if not yet completed (0 IS a mark)
    completed: bool
    group: str = ""         # name of the type this item belongs to ("" = itself)
    items: int = 1          # M — number of items in the type
    count_best: int = 1     # N — how many of them count (1 <= N <= M)
    item_max: float = 100.0  # max mark for this item; ranking uses mark / item_max


@dataclass
class Student:
    student_code: str
    assessments: list[Assessment] = field(default_factory=list)

    @property
    def p_mark_current(self) -> float:
        """Participation accrued so far, with the best-N-of-M rule applied.

        Delegates to the single rule engine (``backend.services.participation``)
        so no other module re-implements the drop rule. For a plan with M = N = 1
        everywhere this is the published p = sum(y_i * w_i) of Van der Merwe et
        al. (2018b).
        """
        from backend.services.participation import final_participation

        return final_participation(self.assessments)


@dataclass
class ClassConfig:
    pass_threshold: float = 50.0
    target_class_average: float = 60.0


@dataclass
class Module:
    """One teaching module: code/name, assessment plan, and enrolled students."""

    code: str
    name: str = ""
    assessments: list[Assessment] = field(default_factory=list)
    students: list[Student] = field(default_factory=list)
    config: ClassConfig = field(default_factory=ClassConfig)

    @property
    def label(self) -> str:
        """Display label, e.g. 'MTHS111 — Calculus 1'."""
        return f"{self.code} — {self.name}" if self.name else self.code

    def assessment(self, name: str) -> Assessment | None:
        """Look up an assessment-plan TYPE by name."""
        for a in self.assessments:
            if a.name == name:
                return a
        return None

    def plan_item_specs(self) -> list[dict]:
        """Flatten the plan's assessment types into their individual items.

        A type with M items becomes M item records named ``"<Type> 1".."<Type> M"``
        (a single-item type keeps the type's own name). Every item carries the
        type's weight W and the pair (M, N) so the participation rule engine can
        work from a bare list of items.
        """
        specs: list[dict] = []
        for entry in self.assessments:
            items = max(1, int(getattr(entry, "items", 1) or 1))
            count_best = max(1, min(int(getattr(entry, "count_best", 1) or 1), items))
            for i in range(items):
                specs.append(
                    {
                "name": entry.name if items <= 1 else f"{entry.name} {i + 1}",
                "group": entry.name,
                "weight": float(entry.weight),
                "items": items,
                "count_best": count_best,
                "item_max": float(getattr(entry, "item_max", 100.0) or 100.0),
            }
                )
        return specs

    def plan_items(self) -> list[Assessment]:
        """The plan as a flat list of blank item records (see ``plan_item_specs``)."""
        return [
            Assessment(
                name=spec["name"],
                weight=spec["weight"],
                mark=None,
                completed=False,
                group=spec["group"],
                items=spec["items"],
                count_best=spec["count_best"],
                item_max=spec["item_max"],
            )
            for spec in self.plan_item_specs()
        ]

    def plan_item(self, name: str) -> Assessment | None:
        """Look up one plan ITEM (as opposed to an assessment type) by name."""
        for item in self.plan_items():
            if item.name == name:
                return item
        return None

    def student(self, student_code: str) -> Student | None:
        """Look up an enrolled student by anonymised code."""
        for s in self.students:
            if s.student_code == student_code:
                return s
        return None

    def student_assessment(self, student: Student, name: str) -> Assessment | None:
        """Look up one of a student's assessments by plan name."""
        for a in student.assessments:
            if a.name == name:
                return a
        return None
