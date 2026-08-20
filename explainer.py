"""
explainer.py

Builds the calm, non-diagnostic, patient-facing explanation text for a
classified laboratory result. All wording here follows the safe-language
rules of the project: no diagnoses, no treatment instructions, only
possibilities and a recommendation to discuss the result with a physician.

The explanation logic is reusable: it does not duplicate medical content -
it only assembles content that already lives in data/lab_tests.json.
"""

from __future__ import annotations

from typing import List

from .data_loader import load_lab_tests
from .models import ClassifiedLabResult

DEFAULT_REFERRAL_TEXT = (
    "ברוב המקרים הצעד הראשון הוא פנייה לרופא/ת המשפחה, "
    "שיוכל/תוכל להחליט האם נדרש בירור נוסף או הפניה לגורם מקצועי."
)

NORMAL_SUMMARY_TEXT = "כל הערכים שנבדקו נמצאים בטווחי הייחוס שהוגדרו באב-הטיפוס."


class ResultExplanation:
    """Container for the structured explanation sections shown in the UI."""

    def __init__(
        self,
        short_summary: str,
        what_it_measures: str,
        possible_reasons: List[str],
        urgency_text: str,
        referral_text: str,
    ):
        self.short_summary = short_summary
        self.what_it_measures = what_it_measures
        self.possible_reasons = possible_reasons
        self.urgency_text = urgency_text
        self.referral_text = referral_text


def _short_summary(result: ClassifiedLabResult) -> str:
    if result.status == "normal":
        return f"{result.name_he} ({result.abbreviation}) נמצא/ת בטווח התקין."
    direction_word = "מעל" if result.direction == "high" else "מתחת ל"
    status_word = "גבולי" if result.status == "borderline" else "מחוץ לטווח המקובל"
    return (
        f"{result.name_he} ({result.abbreviation}) הינו {status_word} "
        f"- הערך {direction_word} טווח הייחוס המקובל באב-הטיפוס."
    )


def explain_result(result: ClassifiedLabResult) -> ResultExplanation:
    """Build a full, non-diagnostic explanation for one classified result.

    For normal results, only a short calm summary is returned - the project
    deliberately avoids overclaiming ("your immune system is healthy") from
    a single normal value.
    """
    lab_tests = load_lab_tests()
    test_config = lab_tests[result.test_key]

    if result.status == "normal":
        return ResultExplanation(
            short_summary=_short_summary(result),
            what_it_measures=test_config["what_it_measures"],
            possible_reasons=[],
            urgency_text="",
            referral_text="",
        )

    reasons_key = result.direction if result.direction in ("low", "high") else "high"
    possible_reasons = test_config.get("possible_reasons", {}).get(reasons_key, [])
    urgency_text = test_config.get("urgency_text", {}).get(result.status, "")

    return ResultExplanation(
        short_summary=_short_summary(result),
        what_it_measures=test_config["what_it_measures"],
        possible_reasons=possible_reasons,
        urgency_text=urgency_text,
        referral_text=DEFAULT_REFERRAL_TEXT,
    )
