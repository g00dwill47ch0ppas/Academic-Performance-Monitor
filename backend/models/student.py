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
    name: str
    weight: float           # w_i, expected in [0, 1]
    mark: float | None      # y_i, None if not yet completed
    completed: bool


@dataclass
class Student:
    student_code: str
    assessments: list[Assessment] = field(default_factory=list)

    @property
    def p_mark_current(self) -> float:
        """p = sum(y_i * w_i) over completed assessments (Van der Merwe et al., 2018b)."""
        return sum(
            a.mark * a.weight for a in self.assessments if a.completed and a.mark is not None
        )


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
        """Look up an assessment-plan entry by name."""
        for a in self.assessments:
            if a.name == name:
                return a
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
