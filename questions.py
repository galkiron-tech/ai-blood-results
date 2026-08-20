"""
questions.py

Generates patient-specific "questions to ask your physician" based on the
actual classified results - never a generic, recycled list.

Two layers:
1. Per-test questions, pulled directly from data/lab_tests.json.
2. Combination questions, added when specific clinically-relevant patterns
   of results occur together (e.g. elevated WBC together with elevated CRP,
   or low hemoglobin together with low ferritin). These combination
   questions are still framed as open questions for the physician, never as
   conclusions.
"""

from __future__ import annotations

from typing import Dict, List

from .data_loader import load_lab_tests
from .models import ClassifiedLabResult

# Combination rules: each entry defines the test/status/direction pattern
# required, and the extra questions to surface when the pattern matches.
_COMBINATION_RULES = [
    {
        "requires": {"wbc": ("high",), "crp": ("high",)},
        "questions": [
            "האם השילוב של WBC ו-CRP מצריך בירור נוסף?",
            "האם התסמינים שלי מתאימים לממצאים?",
            "האם יש צורך בבדיקות נוספות או במעקב קרוב יותר?",
            "מתי כדאי לחזור על הבדיקות?",
        ],
    },
    {
        "requires": {"hemoglobin": ("low",), "ferritin": ("low",)},
        "questions": [
            "האם דפוס הבדיקות יכול להתאים לחסר ברזל?",
            "האם כדאי לברר גורמים אפשריים לאיבוד דם או ספיגה נמוכה?",
            "האם יש צורך בבדיקות נוספות כמו B12 או חומצה פולית?",
            "מהו לוח הזמנים המתאים למעקב?",
        ],
    },
    {
        "requires": {"ldl": ("high",), "hdl": ("low",)},
        "questions": [
            "האם כדאי להעריך את פרופיל השומנים כתמונה כוללת ולא רק לפי ערך בודד?",
            "אילו גורמי סיכון קרדיווסקולריים נוספים כדאי לבדוק?",
        ],
    },
]


def _matches_pattern(
    classified_by_key: Dict[str, ClassifiedLabResult], pattern: Dict[str, tuple]
) -> bool:
    for test_key, allowed_directions in pattern.items():
        result = classified_by_key.get(test_key)
        if result is None:
            return False
        if result.status not in ("borderline", "abnormal"):
            return False
        if result.direction not in allowed_directions:
            return False
    return True


def build_questions_for_result(result: ClassifiedLabResult) -> List[str]:
    """Per-test questions for a single classified result (status != normal)."""
    if result.status == "normal":
        return []
    lab_tests = load_lab_tests()
    test_config = lab_tests[result.test_key]
    reasons_key = result.direction if result.direction in ("low", "high") else "high"
    return list(test_config.get("questions", {}).get(reasons_key, []))


def build_combination_questions(
    classified_results: List[ClassifiedLabResult],
) -> List[str]:
    """Extra questions that only make sense when specific tests co-occur."""
    classified_by_key = {r.test_key: r for r in classified_results}
    combo_questions: List[str] = []
    for rule in _COMBINATION_RULES:
        if _matches_pattern(classified_by_key, rule["requires"]):
            for question in rule["questions"]:
                if question not in combo_questions:
                    combo_questions.append(question)
    return combo_questions


def build_all_questions(classified_results: List[ClassifiedLabResult]) -> List[str]:
    """Full, de-duplicated, scenario-specific question list for the patient."""
    questions: List[str] = []
    for result in classified_results:
        for question in build_questions_for_result(result):
            if question not in questions:
                questions.append(question)
    for question in build_combination_questions(classified_results):
        if question not in questions:
            questions.append(question)
    return questions
