"""
data_loader.py

Responsible for loading the structured medical knowledge (data/lab_tests.json)
and the synthetic demonstration scenarios (data/scenarios.json) from disk.

Keeping this in its own module means the rest of the application never reads
files directly - it only asks data_loader for already-validated Python
objects. This is what allows the medical knowledge to live in JSON while the
application logic stays in Python.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Dict, List

from .models import PatientScenario

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_BASE_DIR, "data")

LAB_TESTS_PATH = os.path.join(_DATA_DIR, "lab_tests.json")
SCENARIOS_PATH = os.path.join(_DATA_DIR, "scenarios.json")


class DataLoadError(Exception):
    """Raised when required configuration data cannot be loaded."""


@lru_cache(maxsize=1)
def load_lab_tests() -> Dict[str, dict]:
    """Load the lab test knowledge base.

    Returns a dict keyed by test_key (e.g. "wbc", "hemoglobin", ...).
    Cached because this file is read frequently but never changes at runtime.
    """
    try:
        with open(LAB_TESTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as exc:
        raise DataLoadError(f"קובץ נתוני הבדיקות לא נמצא: {LAB_TESTS_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError("קובץ נתוני הבדיקות אינו תקין (JSON שגוי).") from exc

    if not isinstance(data, dict) or not data:
        raise DataLoadError("קובץ נתוני הבדיקות ריק או בפורמט לא צפוי.")

    return data


@lru_cache(maxsize=1)
def load_scenarios() -> List[PatientScenario]:
    """Load the synthetic demonstration scenarios as PatientScenario objects."""
    try:
        with open(SCENARIOS_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError as exc:
        raise DataLoadError(f"קובץ התרחישים לא נמצא: {SCENARIOS_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError("קובץ התרחישים אינו תקין (JSON שגוי).") from exc

    if not isinstance(raw, list) or not raw:
        raise DataLoadError("קובץ התרחישים ריק או בפורמט לא צפוי.")

    scenarios = []
    for item in raw:
        scenarios.append(
            PatientScenario(
                id=item["id"],
                name=item["name"],
                age=item["age"],
                sex=item["sex"],
                context=item["context"],
                notes=item.get("notes", ""),
                values=item.get("values", {}),
            )
        )
    return scenarios


def get_test_keys() -> List[str]:
    """Convenience helper: ordered list of supported test keys."""
    return list(load_lab_tests().keys())
