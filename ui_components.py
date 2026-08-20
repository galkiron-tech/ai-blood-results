"""
ui_components.py

All Streamlit / visual-presentation logic lives here, kept separate from the
medical classification logic (classifier.py) and the medical knowledge
(data/lab_tests.json). This module only knows how to *display* things that
other modules already computed.
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd
import streamlit as st

from .explainer import ResultExplanation, explain_result
from .models import ClassifiedLabResult, PatientSummary
from .questions import build_all_questions

STATUS_LABELS = {
    "normal": "🟢 תקין",
    "borderline": "🟡 גבולי",
    "abnormal": "🔴 חריג",
}

STATUS_ORDER = {"abnormal": 0, "borderline": 1, "normal": 2}


def inject_global_css() -> None:
    """Injects the site-wide RTL / healthcare-product visual theme."""
    st.markdown(
        """
        <style>
        html, body, [class*="css"] {
            direction: rtl;
            font-family: "Segoe UI", "Arial Hebrew", Arial, sans-serif;
        }

        .stApp {
            background: linear-gradient(180deg, #eaf6f8 0%, #eef7f4 100%);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1000px;
        }

        h1, h2, h3, h4 {
            text-align: right;
            color: #14464f;
        }

        p, li, span, label, div {
            text-align: right;
        }

        /* Bordered Streamlit containers become soft healthcare "cards" */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #ffffff;
            border-radius: 18px;
            border: 1px solid #dcecef;
            box-shadow: 0 2px 10px rgba(20, 70, 79, 0.06);
            padding: 0.4rem 0.2rem;
        }

        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border-radius: 14px;
            padding: 0.8rem;
            border: 1px solid #dcecef;
        }

        .mx-pill {
            display: inline-block;
            padding: 0.15rem 0.75rem;
            border-radius: 999px;
            font-size: 0.9rem;
            font-weight: 600;
        }
        .mx-pill-normal { background-color: #e3f6ea; color: #1b7a43; }
        .mx-pill-borderline { background-color: #fff4da; color: #8a6300; }
        .mx-pill-abnormal { background-color: #fdeaea; color: #b02a2a; }

        .mx-disclaimer {
            background-color: #f5f8ff;
            border-right: 4px solid #7691f5;
            padding: 0.8rem 1rem;
            border-radius: 10px;
            font-size: 0.9rem;
            color: #33415c;
        }

        .mx-muted {
            color: #5b6b70;
            font-size: 0.92rem;
        }

        table {
            direction: rtl;
        }

        section[data-testid="stSidebar"] {
            background-color: #f4fbfb;
        }

        footer {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: Optional[str] = None) -> None:
    st.markdown(f"## {title}")
    if subtitle:
        st.markdown(f"<div class='mx-muted'>{subtitle}</div>", unsafe_allow_html=True)
    st.write("")


def render_disclaimer(text: str) -> None:
    st.markdown(f"<div class='mx-disclaimer'>{text}</div>", unsafe_allow_html=True)


def status_pill_html(status: str) -> str:
    label = STATUS_LABELS.get(status, status)
    css_class = f"mx-pill mx-pill-{status}" if status in STATUS_LABELS else "mx-pill"
    return f"<span class='{css_class}'>{label}</span>"


def build_results_dataframe(classified_results: List[ClassifiedLabResult]) -> pd.DataFrame:
    """Builds the patient-facing results table using pandas.

    Sorted so abnormal results surface first, then borderline, then normal -
    the most clinically relevant rows are easiest for the patient to find.
    """
    rows = []
    for r in classified_results:
        rows.append(
            {
                "בדיקה": f"{r.name_he} ({r.abbreviation})",
                "תוצאה": r.value,
                "יחידות": r.unit,
                "טווח ייחוס": r.reference_text,
                "סטטוס": STATUS_LABELS.get(r.status, r.status),
                "_sort": STATUS_ORDER.get(r.status, 9),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("_sort").drop(columns="_sort").reset_index(drop=True)
    return df


def render_results_table(classified_results: List[ClassifiedLabResult]) -> None:
    df = build_results_dataframe(classified_results)
    if df.empty:
        st.info("לא הוזנו תוצאות בדיקה להצגה.")
        return
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_summary_card(summary: PatientSummary) -> None:
    with st.container(border=True):
        st.markdown("### סיכום כללי")
        cols = st.columns(3)
        cols[0].metric("תקינים", summary.normal_count)
        cols[1].metric("גבוליים", summary.borderline_count)
        cols[2].metric("חריגים", summary.abnormal_count)
        st.write("")
        st.markdown(summary.summary_text)


def _trend_text(trend: Optional[str]) -> str:
    if trend == "up":
        return "📈 עלה לעומת הבדיקה הקודמת"
    if trend == "down":
        return "📉 ירד לעומת הבדיקה הקודמת"
    if trend == "stable":
        return "➡️ ללא שינוי משמעותי לעומת הבדיקה הקודמת"
    return ""


def render_result_explanation_card(result: ClassifiedLabResult) -> None:
    """Renders the full explanation card for one non-normal result, following
    the required structure: summary, what it measures, possible reasons,
    urgency, referral guidance, and physician questions.
    """
    explanation: ResultExplanation = explain_result(result)

    with st.container(border=True):
        header = f"{status_pill_html(result.status)} &nbsp; **{result.name_he} ({result.abbreviation})**"
        st.markdown(header, unsafe_allow_html=True)
        st.markdown(f"**סיכום קצר:** {explanation.short_summary}")

        trend_text = _trend_text(result.trend)
        if trend_text:
            st.markdown(f"<span class='mx-muted'>{trend_text}</span>", unsafe_allow_html=True)

        st.markdown("**מה הבדיקה מודדת?**")
        st.write(explanation.what_it_measures)

        if explanation.possible_reasons:
            st.markdown("**מה יכול להשפיע על הערך?**")
            for reason in explanation.possible_reasons:
                st.markdown(f"- {reason}")

        if explanation.urgency_text:
            st.markdown("**כמה זה דחוף?**")
            st.write(explanation.urgency_text)

        if explanation.referral_text:
            st.markdown("**למי נכון לפנות?**")
            st.write(explanation.referral_text)

        questions = build_all_questions([result])
        if questions:
            st.markdown("**מה כדאי לשאול את הרופא/ה?**")
            for q in questions:
                st.markdown(f"- {q}")


def render_normal_result_note(classified_results: List[ClassifiedLabResult]) -> None:
    normal_results = [r for r in classified_results if r.status == "normal"]
    if not normal_results:
        return
    names = ", ".join(f"{r.name_he} ({r.abbreviation})" for r in normal_results)
    with st.container(border=True):
        st.markdown(f"{status_pill_html('normal')} &nbsp; **תוצאות תקינות**", unsafe_allow_html=True)
        st.write(f"הבדיקות הבאות נמצאות בטווח התקין: {names}.")
        st.markdown(
            "<span class='mx-muted'>בדיקות בודדות אינן מהוות תמונה רפואית מלאה, "
            "ואינן מהוות אישור למצב בריאותי כללי.</span>",
            unsafe_allow_html=True,
        )
