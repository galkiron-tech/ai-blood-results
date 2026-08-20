"""
summary.py

Builds a structured, non-diagnostic summary across all of a patient's
classified laboratory results: counts by status, key findings worth
discussing, and a short calm summary sentence.
"""

from __future__ import annotations

from typing import List

from .models import ClassifiedLabResult, PatientSummary

NORMAL_ONLY_TEXT = "כל הערכים שנבדקו נמצאים בטווחי הייחוס שהוגדרו באב-הטיפוס."


def build_patient_summary(classified_results: List[ClassifiedLabResult]) -> PatientSummary:
    """Aggregate classified results into a PatientSummary.

    Does not diagnose. Only counts, lists findings by name, and recommends
    discussing multiple co-occurring findings together with a physician when
    more than one non-normal result is present.
    """
    total = len(classified_results)
    normal = [r for r in classified_results if r.status == "normal"]
    borderline = [r for r in classified_results if r.status == "borderline"]
    abnormal = [r for r in classified_results if r.status == "abnormal"]

    key_findings = [f"{r.name_he} ({r.abbreviation})" for r in (abnormal + borderline)]

    if total == 0:
        summary_text = "לא הוזנו תוצאות בדיקה לניתוח."
    elif not borderline and not abnormal:
        summary_text = NORMAL_ONLY_TEXT
    else:
        findings_text = ", ".join(key_findings)
        if len(key_findings) > 1:
            summary_text = (
                f"נמצאו {len(key_findings)} תוצאות שכדאי לדון בהן עם רופא/ת המשפחה: "
                f"{findings_text}. יש לבחון את הממצאים יחד עם התסמינים, "
                "ההיסטוריה הרפואית ובדיקות קודמות."
            )
        else:
            summary_text = (
                f"נמצאה תוצאה אחת שכדאי לדון בה עם רופא/ת המשפחה: {findings_text}. "
                "יש לבחון את הממצא יחד עם התסמינים, ההיסטוריה הרפואית ובדיקות קודמות."
            )

    return PatientSummary(
        total_tests=total,
        normal_count=len(normal),
        borderline_count=len(borderline),
        abnormal_count=len(abnormal),
        key_findings=key_findings,
        summary_text=summary_text,
    )
