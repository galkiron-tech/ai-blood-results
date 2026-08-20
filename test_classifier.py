"""
test_classifier.py

Unit tests for the deterministic, rule-based classification logic in
src/classifier.py. These tests demonstrate that lab-value classification is
reproducible and does not depend on any AI/LLM component.

Run with:
    pytest tests/test_classifier.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.classifier import (
    InvalidLabInputError,
    classify_lab_value,
    compute_trend,
    validate_numeric_value,
)


# ---------------------------------------------------------------------------
# HbA1c (high_concern direction)
# ---------------------------------------------------------------------------

def test_hba1c_normal():
    result = classify_lab_value("hba1c", 5.2)
    assert result.status == "normal"
    assert result.direction is None


def test_hba1c_borderline():
    result = classify_lab_value("hba1c", 6.0)
    assert result.status == "borderline"
    assert result.direction == "high"


def test_hba1c_abnormal():
    result = classify_lab_value("hba1c", 7.1)
    assert result.status == "abnormal"
    assert result.direction == "high"


def test_hba1c_boundary_normal_max_is_normal():
    result = classify_lab_value("hba1c", 5.6)
    assert result.status == "normal"


def test_hba1c_boundary_abnormal_min_is_abnormal():
    result = classify_lab_value("hba1c", 6.5)
    assert result.status == "abnormal"


# ---------------------------------------------------------------------------
# WBC (band direction)
# ---------------------------------------------------------------------------

def test_wbc_normal():
    result = classify_lab_value("wbc", 6.0)
    assert result.status == "normal"


def test_wbc_elevated_borderline():
    result = classify_lab_value("wbc", 10.5)
    assert result.status == "borderline"
    assert result.direction == "high"


def test_wbc_elevated_abnormal():
    result = classify_lab_value("wbc", 13.0)
    assert result.status == "abnormal"
    assert result.direction == "high"


def test_wbc_low_abnormal():
    result = classify_lab_value("wbc", 3.0)
    assert result.status == "abnormal"
    assert result.direction == "low"


# ---------------------------------------------------------------------------
# Sex-specific thresholds (hemoglobin)
# ---------------------------------------------------------------------------

def test_hemoglobin_female_normal():
    result = classify_lab_value("hemoglobin", 13.0, sex="female")
    assert result.status == "normal"


def test_hemoglobin_female_low_abnormal():
    result = classify_lab_value("hemoglobin", 10.0, sex="female")
    assert result.status == "abnormal"
    assert result.direction == "low"


def test_hemoglobin_male_same_value_is_borderline_low():
    # 10.0 is below the male abnormal_low_max threshold too in this PoC's
    # illustrative ranges, so instead we check a value that differs by sex.
    result_male = classify_lab_value("hemoglobin", 12.5, sex="male")
    result_female = classify_lab_value("hemoglobin", 12.5, sex="female")
    assert result_male.status == "borderline"
    assert result_female.status == "normal"


# ---------------------------------------------------------------------------
# Missing / invalid values
# ---------------------------------------------------------------------------

def test_missing_value_raises():
    with pytest.raises(InvalidLabInputError):
        validate_numeric_value(None)


def test_empty_string_raises():
    with pytest.raises(InvalidLabInputError):
        validate_numeric_value("")


def test_non_numeric_value_raises():
    with pytest.raises(InvalidLabInputError):
        validate_numeric_value("abc")


def test_negative_value_raises():
    with pytest.raises(InvalidLabInputError):
        validate_numeric_value(-5)


def test_unreasonably_large_value_raises():
    with pytest.raises(InvalidLabInputError):
        validate_numeric_value(999999)


def test_unknown_test_key_raises():
    with pytest.raises(InvalidLabInputError):
        classify_lab_value("unknown_test", 5.0)


# ---------------------------------------------------------------------------
# Trend computation
# ---------------------------------------------------------------------------

def test_trend_up():
    assert compute_trend(6.2, 5.8) == "up"


def test_trend_down():
    assert compute_trend(5.5, 6.0) == "down"


def test_trend_stable():
    assert compute_trend(5.5, 5.5) == "stable"


def test_trend_none_when_no_previous_value():
    assert compute_trend(5.5, None) is None


def test_trend_ignores_invalid_previous_value():
    assert compute_trend(5.5, "not-a-number") is None
