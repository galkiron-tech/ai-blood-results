"""
app.py

MedExplain AI - main Streamlit entry point.

This file is intentionally an *orchestrator*: it wires together the medical
knowledge (data/lab_tests.json), the deterministic classifier
(src/classifier.py), the explanation/question logic (src/explainer.py,
src/questions.py), the summary engine (src/summary.py) and the UI building
blocks (src/ui_components.py). It does not contain medical thresholds or
medical wording itself - that all lives in data/ and src/.

Run locally:
    streamlit run app.py
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional

# Defensive fix: make sure the directory containing this file (the repo
# root, where the `src` package lives) is on sys.path. Most local/Streamlit
# Cloud setups already have this, but some deployment configurations run
# the script from a different working directory, which otherwise causes
# "ModuleNotFoundError: No module named 'src'".
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

import streamlit as st

from src.classifier import (
    InvalidLabInputError,
    classify_lab_value,
    compute_trend,
    validate_numeric_value,
)
from src.data_loader import DataLoadError, get_test_keys, load_lab_tests, load_scenarios
from src.models import ClassifiedLabResult, PatientScenario
from src.questions import build_all_questions
from src.summary import build_patient_summary
from src.ui_components import (
    inject_global_css,
    render_disclaimer,
    render_normal_result_note,
    render_page_header,
    render_result_explanation_card,
    render_results_table,
    render_summary_card,
)

st.set_page_config(
    page_title="MedExplain AI",
    page_icon="🩺",
    layout="centered",
)

PAGES = [
    "עמוד הבית",
    "לוח מטופל",
    "כיצד זה עובד",
    "למה לא ChatGPT?",
    "בטיחות ואתיקה",
    "משוב מהמטופל",
    "ארכיטקטורת המערכת",
]

TREND_ENABLED_TESTS = ["hba1c", "ldl", "hemoglobin", "crp"]

GENERAL_DISCLAIMER = (
    "המערכת נועדת להדגמה לימודית בלבד ואינה תחליף לייעוץ רפואי, לאבחון או לטיפול. "
    "טווחי הייחוס המוצגים הם ערכים לדוגמה, ואינם מחליפים את טווח הייחוס של המעבדה "
    "המבצעת את הבדיקה או את פרשנות הרופא/ה המטפל/ת."
)


# ---------------------------------------------------------------------------
# Classification pipeline helpers
# ---------------------------------------------------------------------------

def classify_scenario(scenario: PatientScenario) -> List[ClassifiedLabResult]:
    """Runs the full pipeline for a synthetic scenario (Mode A)."""
    results: List[ClassifiedLabResult] = []
    for test_key, value in scenario.values.items():
        try:
            result = classify_lab_value(test_key, value, sex=scenario.sex, age=scenario.age)
            results.append(result)
        except InvalidLabInputError as exc:
            st.warning(f"שגיאה בעיבוד הבדיקה '{test_key}': {exc}")
    return results


def classify_manual_input(
    values: Dict[str, str],
    previous_values: Dict[str, str],
    sex: Optional[str],
    age: Optional[int],
) -> List[ClassifiedLabResult]:
    """Runs the full pipeline for manually entered values (Mode B).

    Only tests with a non-empty value are analyzed. Invalid entries produce a
    calm Hebrew error message rather than crashing the app.
    """
    results: List[ClassifiedLabResult] = []
    lab_tests = load_lab_tests()

    for test_key in lab_tests.keys():
        raw_value = values.get(test_key, "")
        if raw_value in (None, ""):
            continue
        try:
            numeric_value = validate_numeric_value(raw_value)
            result = classify_lab_value(test_key, numeric_value, sex=sex, age=age)
        except InvalidLabInputError as exc:
            display_name = lab_tests[test_key]["name_he"]
            st.error(f"שגיאה בבדיקת {display_name}: {exc}")
            continue

        raw_prev = previous_values.get(test_key, "")
        if raw_prev not in (None, ""):
            try:
                prev_numeric = validate_numeric_value(raw_prev)
                result.trend = compute_trend(result.value, prev_numeric)
            except InvalidLabInputError:
                pass  # trend is optional; ignore invalid previous value quietly

        results.append(result)

    return results


def render_analysis_results(classified_results: List[ClassifiedLabResult]) -> None:
    """Shared rendering logic used by both Mode A and Mode B after classification."""
    if not classified_results:
        st.info("לא נמצאו תוצאות תקפות לניתוח. נא להזין לפחות ערך אחד.")
        return

    st.write("")
    st.markdown("### טבלת תוצאות")
    render_results_table(classified_results)

    st.write("")
    summary = build_patient_summary(classified_results)
    render_summary_card(summary)

    non_normal = [r for r in classified_results if r.status != "normal"]
    if non_normal:
        st.write("")
        st.markdown("### הסברים מותאמים לתוצאות")
        for result in non_normal:
            render_result_explanation_card(result)

    render_normal_result_note(classified_results)

    combo_note = build_all_questions(classified_results)
    if len(non_normal) > 1 and combo_note:
        st.write("")
        with st.container(border=True):
            st.markdown("### שילוב ממצאים")
            st.write(
                "כאשר קיימות מספר תוצאות שאינן תקינות בו-זמנית, מומלץ להביא אותן יחד "
                "לשיחה עם הרופא/ה, מכיוון שהמשמעות הקלינית עשויה להיות שונה מהתייחסות "
                "לכל ממצא בנפרד."
            )


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def page_home() -> None:
    render_page_header(
        "MedExplain AI",
        "מערכת AI להסבר והנגשת תוצאות בדיקות דם למטופלים - פרויקט גמר בקורס בינה מלאכותית ברפואה",
    )

    with st.container(border=True):
        st.markdown("### הבעיה")
        st.write(
            "מטופלים רבים מקבלים תוצאות בדיקות דם באופן דיגיטלי עוד לפני שיחה עם הרופא/ה "
            "המטפל/ת. כאשר מופיע ערך אדום או חריג, קשה להבין מה הוא מודד, האם מדובר בסטייה "
            "קלה או משמעותית, והאם יש הקשר בין התוצאות השונות. הדבר עלול להוביל לחרדה "
            "מיותרת, לחיפושים לא מבוקרים ברשת, ולעיתים אף להעתקת מידע רפואי אישי לכלי AI "
            "ציבוריים."
        )

    with st.container(border=True):
        st.markdown("### הפתרון המוצע")
        st.write(
            "MedExplain AI הוא שכבת הסבר המבוססת על נתונים רפואיים מובנים וסיווג "
            "דטרמיניסטי מבוסס-כללים, שנועדה לגשר בין קבלת תוצאות המעבדה לבין השיחה עם "
            "הרופא/ה - ולא להחליף אותה."
        )

    with st.container(border=True):
        st.markdown("### חשוב להבהיר")
        st.write(
            "המערכת אינה קובעת אבחנות, אינה ממליצה על טיפול, ואינה מחליפה את הרופא/ה "
            "המטפל/ת. מטרתה היחידה היא לסייע למטופל/ת להבין את תוצאות הבדיקה ולהגיע "
            "מוכן/ה יותר לשיחה הרפואית."
        )

    render_disclaimer(GENERAL_DISCLAIMER)

    st.write("")
    st.info("לניסוי המערכת, יש לעבור לעמוד **לוח מטופל** בתפריט הצדדי.")


def _scenario_selector_label(scenario: PatientScenario) -> str:
    sex_label = "זכר" if scenario.sex == "male" else "נקבה"
    return f"{scenario.name} · גיל {scenario.age} · {sex_label}"


def page_patient_dashboard() -> None:
    render_page_header("לוח מטופל", "בחרו תרחיש הדגמה סינתטי, או הזינו ערכים באופן ידני.")
    render_disclaimer(GENERAL_DISCLAIMER)
    st.write("")

    mode = st.radio(
        "אופן השימוש",
        options=["תרחישי הדגמה סינתטיים", "הזנה ידנית"],
        horizontal=True,
    )

    st.write("")

    if mode == "תרחישי הדגמה סינתטיים":
        try:
            scenarios = load_scenarios()
        except DataLoadError as exc:
            st.error(f"שגיאה בטעינת התרחישים: {exc}")
            return

        labels = [_scenario_selector_label(s) for s in scenarios]
        selected_label = st.selectbox("בחרו מטופל/ת סינתטי/ת", options=labels)
        scenario = scenarios[labels.index(selected_label)]

        with st.container(border=True):
            st.markdown(f"### {scenario.name}")
            st.markdown(f"**הקשר קליני:** {scenario.context}")
            if scenario.notes:
                st.markdown(f"<span class='mx-muted'>{scenario.notes}</span>", unsafe_allow_html=True)

        st.caption("שימו לב: כל דמויות המטופלים בתרחישים אלו הן דמויות סינתטיות בלבד, ואינן מבוססות על מטופלים אמיתיים.")

        classified_results = classify_scenario(scenario)
        render_analysis_results(classified_results)

    else:
        lab_tests = load_lab_tests()
        test_keys = get_test_keys()

        with st.form("manual_input_form"):
            col1, col2 = st.columns(2)
            with col1:
                age = st.number_input("גיל", min_value=0, max_value=120, value=40, step=1)
            with col2:
                sex_label = st.selectbox("מין", options=["נקבה", "זכר"])
                sex = "female" if sex_label == "נקבה" else "male"

            st.markdown("#### ערכי בדיקות (ניתן להשאיר ריק אם אין נתון)")

            values: Dict[str, str] = {}
            previous_values: Dict[str, str] = {}

            for test_key in test_keys:
                test_config = lab_tests[test_key]
                label = f"{test_config['name_he']} ({test_config['abbreviation']}) - {test_config['unit']}"
                if test_key in TREND_ENABLED_TESTS:
                    vcol, pcol = st.columns(2)
                    values[test_key] = vcol.text_input(label, value="", key=f"val_{test_key}")
                    previous_values[test_key] = pcol.text_input(
                        f"ערך קודם ({test_config['abbreviation']}) - אופציונלי",
                        value="",
                        key=f"prev_{test_key}",
                    )
                else:
                    values[test_key] = st.text_input(label, value="", key=f"val_{test_key}")

            submitted = st.form_submit_button("ניתוח תוצאות")

        if submitted:
            classified_results = classify_manual_input(values, previous_values, sex=sex, age=int(age))
            render_analysis_results(classified_results)


def page_how_it_works() -> None:
    render_page_header("כיצד זה עובד", "מסלול הנתונים במערכת, מהזנה ועד להסבר המוצג למטופל.")

    steps = [
        ("1. הזנת נתונים", "המשתמש/ת בוחר/ת תרחיש הדגמה סינתטי, או מזין/ה ערכי בדיקות באופן ידני."),
        ("2. אימות קלט", "המערכת בודקת שהערכים שהוזנו הם מספריים, לא שליליים וסבירים, ומציגה הודעת שגיאה רגועה בעברית במקרה הצורך."),
        ("3. סיווג מבוסס-כללים", "כל ערך נבדק מול טווחי ייחוס מוגדרים מראש (המאוחסנים ב-JSON), וממוין באופן דטרמיניסטי ל'תקין', 'גבולי' או 'חריג'."),
        ("4. בחירת הסבר ושאלות", "בהתאם לסיווג, המערכת בוחרת טקסט הסבר לא-אבחוני ורשימת שאלות ייעודיות לרופא/ה - הכול מתוך תוכן מוגדר מראש."),
        ("5. הצגה למטופל", "התוצאות, ההסברים והשאלות מוצגים בממשק עברי נגיש וברור, בליווי הבהרות בטיחות."),
    ]

    for title, description in steps:
        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.write(description)

    st.write("")
    render_disclaimer(
        "חשוב: הסיווג הרפואי (תקין/גבולי/חריג) מתבצע כולו על ידי לוגיקה דטרמיניסטית מבוססת "
        "כללים, ולא על ידי מודל שפה. מודל שפה (LLM) לא היה מעורב בקבלת ההחלטה הקלינית "
        "בזמן ריצה - הוא שימש רק בתהליך הפיתוח של המערכת."
    )


def page_why_not_chatgpt() -> None:
    render_page_header("למה לא ChatGPT?", "השוואה בין שימוש ב-AI כללי לבין גישה מובנית ומבוקרת.")

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("#### 🌐 AI כללי-ציבורי")
            st.markdown("- המטופל/ת מעתיק/ה ידנית מידע רפואי אישי")
            st.markdown("- הקשר קליני מובנה מוגבל")
            st.markdown("- אפשרות לתגובות לא עקביות בין שיחה לשיחה")
            st.markdown("- המידע עשוי לצאת ממערך הבריאות המוסדר")
            st.markdown("- אין חיבור ישיר לתהליך הטיפול מול הרופא/ה")

    with col2:
        with st.container(border=True):
            st.markdown("#### 🩺 גישת MedExplain")
            st.markdown("- נתוני מעבדה מובנים")
            st.markdown("- סיווג ראשוני דטרמיניסטי ואחיד")
            st.markdown("- הסברים מבוקרים בהתאם לכללי בטיחות מוגדרים")
            st.markdown("- גבולות בטיחות ברורים ומפורשים")
            st.markdown("- מיועד לסייע בהכנה לשיחה עם הרופא/ה")
            st.markdown("- בעתיד - פוטנציאל לשילוב בתשתית שירותי הבריאות")

    st.write("")
    render_disclaimer(
        "חשוב להיות מדויקים: המערכת אינה מבטיחה פרטיות או אבטחה מוחלטת. מדובר באב-טיפוס "
        "לימודי המדגים כיוון אפשרי, ולא במוצר ייצור."
    )


def page_safety_ethics() -> None:
    render_page_header("בטיחות ואתיקה", "עקרונות הבטיחות הקליניים והאתיים שעליהם מבוססת המערכת.")

    with st.container(border=True):
        st.markdown("#### מה המערכת כן עושה")
        st.markdown("- מספקת תמיכה חינוכית-הסברתית בלבד")
        st.markdown("- מציגה סיווג דטרמיניסטי מבוסס טווחי ייחוס לדוגמה")
        st.markdown("- מסייעת בהכנת שאלות לשיחה עם הרופא/ה")

    with st.container(border=True):
        st.markdown("#### מה המערכת לא עושה")
        st.markdown("- אינה קובעת אבחנות")
        st.markdown("- אינה ממליצה על טיפול תרופתי או אחר")
        st.markdown("- אינה מחליפה את שיקול הדעת הרפואי - הרופא/ה נשאר/ת גורם הסמכות הקליני הסופי")

    with st.container(border=True):
        st.markdown("#### מגבלות ידועות")
        st.markdown("- טווחי ייחוס עשויים להשתנות בין מעבדות שונות")
        st.markdown("- קיים סיכון תיאורטי לתוצאה שגויה או להטיה ('hallucination') בכל רכיב מבוסס-AI בתהליך הפיתוח")
        st.markdown("- קיים סיכון להרגעת יתר (over-reassurance) בערכים גבוליים")
        st.markdown("- שונות בין אוכלוסיות (גיל, מין, רקע קליני) אינה מיוצגת במלואה באב-הטיפוס")
        st.markdown("- הבדלים באוריינות בריאותית בין משתמשים שונים")
        st.markdown("- נגישות ותמיכה בשפות/אוכלוסיות נוספות טרם נבדקה")
        st.markdown("- נדרש אימות קליני פורמלי לפני כל שימוש מעבר להדגמה לימודית")

    with st.container(border=True):
        st.markdown("#### נתונים סינתטיים בלבד")
        st.write(
            "כל תרחישי ההדגמה במערכת מבוססים על דמויות סינתטיות בלבד. לא נעשה שימוש "
            "במידע רפואי אמיתי של מטופלים."
        )

    st.write("")
    render_disclaimer(
        "יש להבחין בין 'נכונות טכנית' (הקוד פועל כמצופה) לבין 'בטיחות קלינית' (הפלט "
        "בטוח, מדויק ואחראי מבחינה רפואית). עמידה בדרישה הראשונה אינה מבטיחה עמידה בשנייה, "
        "ולכן נדרשת בקרה קלינית מקצועית לפני כל שימוש מעבר לפרויקט לימודי."
    )


def page_feedback() -> None:
    render_page_header("משוב מהמטופל", "המשוב אינו נשמר לצמיתות - מדובר בהדגמה מבוססת-מפגש (session) בלבד.")

    with st.form("feedback_form"):
        q1 = st.slider("עד כמה ההסבר היה ברור?", min_value=1, max_value=5, value=3)
        q2 = st.slider("האם ההסבר עזר לך להבין את משמעות התוצאה?", min_value=1, max_value=5, value=3)
        q3 = st.radio("האם ברור לך יותר מה כדאי לשאול את הרופא?", options=["כן", "חלקית", "לא"])
        q4 = st.radio(
            "האם ההסבר הפחית את רמת החשש שלך?",
            options=["כן מאוד", "במידה מסוימת", "לא", "לא רלוונטי"],
        )
        q5 = st.radio("האם היית משתמש/ת בכלי כזה באפליקציית קופת החולים?", options=["כן", "אולי", "לא"])
        q6 = st.text_area("מה עדיין לא היה ברור?", value="")

        submitted = st.form_submit_button("שליחת משוב")

    if submitted:
        st.session_state.setdefault("feedback_log", []).append(
            {
                "בהירות ההסבר": q1,
                "מידת הסיוע בהבנה": q2,
                "בהירות שאלות לרופא": q3,
                "הפחתת חשש": q4,
                "נכונות לשימוש עתידי": q5,
                "הערה חופשית": q6,
            }
        )
        st.success("תודה על המשוב! המשוב נשמר לצורך הדגמה בלבד במהלך הסשן הנוכחי.")

    feedback_log = st.session_state.get("feedback_log", [])
    if feedback_log:
        st.write("")
        st.markdown(f"#### משובים שהוזנו בסשן זה ({len(feedback_log)})")
        for i, entry in enumerate(reversed(feedback_log), start=1):
            with st.container(border=True):
                st.markdown(f"**משוב #{len(feedback_log) - i + 1}**")
                for key, val in entry.items():
                    if val:
                        st.markdown(f"- **{key}:** {val}")


def page_architecture() -> None:
    render_page_header("ארכיטקטורת המערכת", "תרשים זרימה טכני להערכת המנחה/בוחן/ת.")

    flow_steps = [
        "נתוני בדיקות מובנים (data/lab_tests.json)",
        "אימות קלט (src/classifier.py)",
        "מנוע סיווג מבוסס-כללים (src/classifier.py)",
        "בחירת הסבר ושאלות (src/explainer.py, src/questions.py)",
        "מנגנוני בטיחות (ניסוח מבוקר, ללא אבחון)",
        "ממשק פונה למטופל (src/ui_components.py + app.py)",
    ]

    for i, step in enumerate(flow_steps, start=1):
        with st.container(border=True):
            st.markdown(f"**שלב {i}:** {step}")
        if i < len(flow_steps):
            st.markdown("<div style='text-align:center; font-size:1.4rem;'>⬇️</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown("### רכיבי הטכנולוגיה")
    tech_table = {
        "Python": "לוגיקת הליבה של האפליקציה - סיווג, הסברים, ניהול מצב.",
        "JSON": "ידע רפואי מובנה וניתן לעדכון (טווחי ייחוס, הסברים, שאלות) - נפרד מקוד האפליקציה.",
        "Pandas": "בניית טבלת התוצאות, ארגון ערכים/יחידות/סיווגים לצורך הצגה.",
        "Streamlit": "אב-טיפוס אינטראקטיבי להדגמת המערכת.",
        "CSS / RTL": "ממשק פונה-מטופל בעברית, מיושר מימין לשמאל.",
        "GitLab": "ניהול גרסאות במהלך הפיתוח (אינו חלק מזמן הריצה של האפליקציה).",
        "סיוע LLM": "שימש בפיתוח ניסוח טקסטים/פרומפטים בשלב הפיתוח - לא לצורך קבלת החלטות קליניות בזמן ריצה.",
        "Base44": "שימש בשלב מוקדם יותר של אב-טיפוס חזותי בתהליך הפרויקט (רלוונטי להיסטוריית הפרויקט בלבד).",
    }
    for tech, desc in tech_table.items():
        with st.container(border=True):
            st.markdown(f"**{tech}**")
            st.write(desc)

    st.write("")
    render_disclaimer(
        "GitLab אינו חלק מארכיטקטורת זמן-הריצה של האפליקציה - הוא שימש אך ורק לניהול "
        "גרסאות במהלך הפיתוח."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    inject_global_css()

    st.sidebar.markdown("### MedExplain AI")
    st.sidebar.caption("מערכת AI להסבר והנגשת תוצאות בדיקות דם למטופלים")
    page = st.sidebar.radio("ניווט", options=PAGES, label_visibility="collapsed")

    page_functions = {
        "עמוד הבית": page_home,
        "לוח מטופל": page_patient_dashboard,
        "כיצד זה עובד": page_how_it_works,
        "למה לא ChatGPT?": page_why_not_chatgpt,
        "בטיחות ואתיקה": page_safety_ethics,
        "משוב מהמטופל": page_feedback,
        "ארכיטקטורת המערכת": page_architecture,
    }

    page_functions[page]()


if __name__ == "__main__":
    main()
