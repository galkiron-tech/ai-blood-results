"""
classifier.py

Deterministic, rule-based classification of laboratory values.

This is the clinical-safety core of the application: an AI/LLM is never used
to decide whether a value is normal, borderline, or abnormal. Every decision
here is a plain, auditable, reproducible if/else comparison against
thresholds stored in data/lab_tests.json.

Public API:
    classify_lab_value(test_key, value, sex=None, age=None) -> ClassifiedLabResult
"""

from __future__ import annotations

from typing import Optional

from .data_loader import load_lab_tests, DataLoadError
from .models import ClassifiedLabResult


class InvalidLabInputError(Exception):
    """Raised when the input to the classifier cannot be safely interpreted."""


def _resolve_thresholds(test_config: dict, sex: Optional[str]) -> dict:
    """Pick the correct threshold set for the given sex, falling back to default."""
    thresholds = test_config.get("thresholds", {})
    if sex in ("male", "female") and sex in thresholds:
        return thresholds[sex]
    if "default" in thresholds:
        return thresholds["default"]
    # Fall back to any available threshold set as a last resort.
    if thresholds:
        return next(iter(thresholds.values()))
    raise InvalidLabInputError(f"לא הוגדרו טווחי ייחוס עבור הבדיקה '{test_config.get('key')}'.")


def _format_reference_text(test_config: dict, thresholds: dict) -> str:
    direction = test_config["direction"]
    unit = test_config["unit"]
    if direction == "band":
        return f"{thresholds['normal_min']}–{thresholds['normal_max']} {unit}"
    if direction == "high_concern":
        return f"עד {thresholds['normal_max']} {unit}"
    if direction == "low_concern":
        return f"מעל {thresholds['normal_min']} {unit}"
    return "טווח ייחוס לא זמין"


def _classify_band(value: float, thresholds: dict) -> tuple[str, Optional[str]]:
    if value < thresholds["abnormal_low_max"]:
        return "abnormal", "low"
    if value < thresholds["normal_min"]:
        return "borderline", "low"
    if value <= thresholds["normal_max"]:
        return "normal", None
    if value <= thresholds["abnormal_high_min"]:
        return "borderline", "high"
    return "abnormal", "high"


def _classify_high_concern(value: float, thresholds: dict) -> tuple[str, Optional[str]]:
    if value <= thresholds["normal_max"]:
        return "normal", None
    if value < thresholds["abnormal_high_min"]:
        return "borderline", "high"
    return "abnormal", "high"


def _classify_low_concern(value: float, thresholds: dict) -> tuple[str, Optional[str]]:
    if value >= thresholds["normal_min"]:
        return "normal", None
    if value >= thresholds["abnormal_low_max"]:
        return "borderline", "low"
    return "abnormal", "low"


_DIRECTION_HANDLERS = {
    "band": _classify_band,
    "high_concern": _classify_high_concern,
    "low_concern": _classify_low_concern,
}


def validate_numeric_value(raw_value) -> float:
    """Validate and convert raw user input into a safe float.

    Raises InvalidLabInputError with a calm Hebrew message on any problem.
    """
    if raw_value is None or raw_value == "":
        raise InvalidLabInputError("לא הוזן ערך.")
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        raise InvalidLabInputError("הערך שהוזן אינו מספרי.")
    if value < 0:
        raise InvalidLabInputError("לא ניתן להזין ערך שלילי.")
    if value > 100000:
        raise InvalidLabInputError("הערך שהוזן אינו סביר. נא לבדוק שוב.")
    return value


def classify_lab_value(
    test_key: str,
    value: float,
    sex: Optional[str] = None,
    age: Optional[int] = None,
) -> ClassifiedLabResult:
    """Classify a single laboratory value against configured reference ranges.

    Args:
        test_key: key identifying the test, e.g. "wbc", "hba1c".
        value: the numeric lab value (already validated).
        sex: "male" | "female" | None - used to select sex-specific ranges.
        age: currently accepted for future extensibility (not all tests use it).

    Returns:
        ClassifiedLabResult with status "normal" | "borderline" | "abnormal".

    Raises:
        InvalidLabInputError: for unknown test keys or invalid values.
    """
    try:
        lab_tests = load_lab_tests()
    except DataLoadError as exc:
        raise InvalidLabInputError(str(exc)) from exc

    if test_key not in lab_tests:
        raise InvalidLabInputError(f"בדיקה לא מוכרת במערכת: '{test_key}'.")

    value = validate_numeric_value(value)

    test_config = lab_tests[test_key]
    thresholds = _resolve_thresholds(test_config, sex)
    direction = test_config["direction"]

    handler = _DIRECTION_HANDLERS.get(direction)
    if handler is None:
        raise InvalidLabInputError(f"סוג סיווג לא מוכר עבור הבדיקה '{test_key}'.")

    status, value_direction = handler(value, thresholds)
    reference_text = _format_reference_text(test_config, thresholds)

    return ClassifiedLabResult(
        test_key=test_key,
        name_he=test_config["name_he"],
        abbreviation=test_config["abbreviation"],
        value=value,
        unit=test_config["unit"],
        status=status,
        direction=value_direction,
        reference_text=reference_text,
    )


def compute_trend(current_value: float, previous_value: Optional[float]) -> Optional[str]:
    """Compare current vs. previous value without implying causality.

    Returns "up" | "down" | "stable" | None (None if no previous value given).
    """
    if previous_value is None:
        return None
    try:
        previous_value = float(previous_value)
    except (TypeError, ValueError):
        return None
    if current_value > previous_value:
        return "up"
    if current_value < previous_value:
        return "down"
    return "stable"
