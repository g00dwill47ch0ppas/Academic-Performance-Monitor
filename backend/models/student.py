"""
Core data model for the DSS artefact.

An Assessment represents one formative-assessment component for one student
(class test, assignment, practical, attendance, etc.). A Student is the set of
assessments for one anonymised student code. ClassConfig holds lecturer-adjustable
settings that affect the algorithms (pass threshold, target class average).
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
