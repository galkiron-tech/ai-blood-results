"""
models.py

Lightweight data model for MedExplain AI.

These dataclasses give the application a real, typed data structure instead
of passing loose dictionaries between the UI and the classification logic.
They intentionally stay simple so the architecture remains easy to explain
in a course presentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class Patient:
    """Minimal, non-identifying demographic information used for classification.

    Only age and sex are stored. Sex is used strictly to select the correct
    reference range (e.g. hemoglobin, ferritin, HDL differ by sex). No
    identifying information (name, ID number, etc.) is required or stored.
    """
    age: Optional[int] = None
    sex: Optional[str] = None  # "male" | "female" | None
    display_name: Optional[str] = None  # only used for synthetic demo scenarios


@dataclass
class LabResult:
    """A single raw laboratory value entered by the user or loaded from a scenario."""
    test_key: str
    value: float
    previous_value: Optional[float] = None


@dataclass
class ClassifiedLabResult:
    """The output of the deterministic classification engine for one test.

    status: "normal" | "borderline" | "abnormal"
    direction: "low" | "high" | None (None when status == "normal")
    """
    test_key: str
    name_he: str
    abbreviation: str
    value: float
    unit: str
    status: str
    direction: Optional[str]
    reference_text: str
    trend: Optional[str] = None  # "up" | "down" | "stable" | None


@dataclass
class PatientScenario:
    """A full synthetic demonstration scenario (Mode A)."""
    id: str
    name: str
    age: int
    sex: str
    context: str
    notes: str
    values: Dict[str, float] = field(default_factory=dict)


@dataclass
class PatientSummary:
    """Aggregated, non-diagnostic summary across all classified results."""
    total_tests: int
    normal_count: int
    borderline_count: int
    abnormal_count: int
    key_findings: List[str]
    summary_text: str
