# MedExplain AI

**מערכת AI להסבר והנגשת תוצאות בדיקות דם למטופלים**

> This prototype is for educational demonstration only and is not a medical device.

A university Medical AI Proof of Concept (PoC) that demonstrates how a
structured, rule-based, safety-conscious explanation layer could help
patients understand their blood test results before speaking with a
physician — without replacing that physician.

---

## Project overview

MedExplain AI is a Streamlit application that takes laboratory values
(either from synthetic demo scenarios or manual patient input), classifies
them deterministically against configurable reference ranges, and generates
calm, non-diagnostic, Hebrew explanations plus a list of physician-specific
questions the patient can bring to their next appointment.

It is explicitly designed as a **hybrid PoC**:

- Deterministic, rule-based medical classification (no AI/LLM in the runtime
  decision path).
- Structured, editable medical knowledge stored in JSON.
- AI/LLM assistance was used only during **development** (drafting
  explanation text, prompt/spec iteration) — never at runtime to decide
  whether a result is normal, borderline, or abnormal.

## Clinical problem

Patients frequently see their laboratory results digitally before discussing
them with a physician. An unexplained red or abnormal value can lead to:

- unnecessary anxiety,
- uncontrolled Google searches,
- copying personal medical data into public AI tools,
- misunderstanding of what a "borderline" or "abnormal" value actually means,
- a poorly prepared physician conversation.

MedExplain AI aims to bridge the gap between *receiving* lab data and
*understanding* it — while explicitly supporting, not replacing, the
patient–physician relationship.

## Target users

- Patients who received digital blood test results and want a calm, initial
  explanation before their appointment.
- (In this academic context) course evaluators assessing the technical and
  clinical-safety architecture of the PoC.

## Architecture

```
Structured lab data (data/lab_tests.json)
        ↓
Input validation (src/classifier.py)
        ↓
Rule-based classification engine (src/classifier.py)
        ↓
Explanation / question selection (src/explainer.py, src/questions.py)
        ↓
Safety guardrails (non-diagnostic wording enforced in content + code)
        ↓
Patient-facing UI (src/ui_components.py + app.py)
```

The classification decision (normal / borderline / abnormal) is made
**entirely by deterministic Python comparisons against thresholds stored in
JSON**. No language model participates in that decision at runtime.

## Technology stack

| Technology   | Role |
|--------------|------|
| Python       | Core application logic: classification, explanation selection, state management |
| Streamlit    | Interactive prototype / UI framework |
| Pandas       | Building and organizing the patient results table |
| JSON         | Structured, editable medical knowledge (reference ranges, explanations, questions) — kept separate from application code |
| CSS          | Hebrew RTL styling and healthcare-product visual design |
| GitLab       | Version control during development (not part of the runtime architecture) |
| LLM assistance | Used during development to help draft language/prompts — not used for real-time clinical classification |

No database, authentication system, Docker/Kubernetes setup, paid API, or
EHR connection is required or used.

## Folder structure

```
medexplain-ai/
│
├── app.py                  # Streamlit entry point / page orchestration
├── requirements.txt
├── README.md
├── .gitignore
│
├── data/
│   ├── lab_tests.json      # Structured medical knowledge (reference ranges, explanations, questions)
│   └── scenarios.json      # 12 synthetic demonstration patient scenarios
│
├── src/
│   ├── __init__.py
│   ├── models.py            # Patient, LabResult, ClassifiedLabResult, PatientScenario, PatientSummary
│   ├── classifier.py         # Deterministic rule-based classification engine
│   ├── explainer.py          # Non-diagnostic explanation text builder
│   ├── questions.py          # Scenario-specific "ask your physician" question builder
│   ├── summary.py            # Aggregated patient summary (counts, key findings)
│   ├── data_loader.py        # Loads/validates JSON configuration from disk
│   └── ui_components.py      # Streamlit UI building blocks (RTL CSS, cards, tables)
│
└── tests/
    └── test_classifier.py    # Unit tests for the classification engine
```

## How to install

```bash
pip install -r requirements.txt
```

## How to run

```bash
streamlit run app.py
```

The app also runs unmodified on Streamlit Community Cloud (no secrets,
database, or external API keys required).

To run the unit tests:

```bash
pytest tests/test_classifier.py -v
```

## How the classification works

1. A laboratory value (from a synthetic scenario or manual entry) is
   validated: must be numeric, non-negative, and within a plausible range.
2. The correct threshold set is selected from `data/lab_tests.json`
   (sex-specific ranges are used for hemoglobin, ferritin, and HDL where
   clinically relevant).
3. Each test is classified using one of three simple comparison patterns:
   - **band** (e.g. WBC, hemoglobin, ferritin): both a low and a high
     abnormal boundary exist.
   - **high_concern** (e.g. LDL, triglycerides, CRP, HbA1c): only high
     values are flagged.
   - **low_concern** (e.g. HDL): only low values are flagged.
4. The result is one of three statuses: `normal`, `borderline`, `abnormal`,
   each with a `direction` (`low`/`high`) when relevant.
5. Non-normal results are matched to pre-written, non-diagnostic explanation
   text and physician-question templates from the same JSON file.
6. A small set of **combination rules** (`src/questions.py`) adds extra
   questions when clinically-relevant patterns co-occur (e.g. elevated WBC
   together with elevated CRP, or low hemoglobin together with low
   ferritin).

## Why deterministic classification was chosen

Clinical classification of a lab value (normal / borderline / abnormal)
needs to be **reproducible, auditable, and explainable**. A rule-based
engine guarantees the same input always produces the same output, and any
evaluator can read the exact threshold used. An LLM-based classification
step would introduce unpredictability that is inappropriate for this part
of the pipeline — so it was deliberately excluded from the clinical
decision path.

## Role of AI/LLMs in this project

- **Not used** at runtime to classify lab values or decide clinical status.
- **Used during development** to help draft and iterate on patient-facing
  Hebrew language, project specification, and documentation.
- The "ארכיטקטורת המערכת" (System Architecture) page in the app makes this
  distinction explicit for evaluators.

## Safety boundaries

The application never states a diagnosis, never recommends a specific
treatment, and never tells the patient a finding is dangerous. All wording
uses careful, non-alarmist language (e.g. "the value is above the typical
reference range", "this may be related to several possible factors",
"recommended to discuss with your family physician") and always points back
to the physician as the next step. See the in-app "בטיחות ואתיקה" page for
the full list of safety principles and known limitations.

## Privacy

- Only synthetic patient data is used throughout the PoC.
- No real Electronic Health Record (EHR) system is connected.
- No medical information is sent to an external LLM at runtime — the entire
  classification and explanation pipeline runs locally within the Streamlit
  app using pre-written content and deterministic logic.
- The privacy argument for a future integrated system is that it could
  **reduce** the need for patients to manually paste medical data into
  public AI tools — not that this current Streamlit prototype itself
  provides production-grade medical security. It does not.

A future production deployment inside an HMO would additionally require:
authentication, role-based access control, encryption in transit and at
rest, secure secrets management, audit logging, monitoring, minimization of
identifiable information, compliance with relevant Israeli medical privacy
regulations, and a formal security review. **None of these are implemented
in this PoC.**

## Limitations

- Reference ranges used in this PoC are **illustrative values for
  demonstration only**. Real laboratory reference intervals vary between
  labs and should always be interpreted together with the specific lab's
  own reported range and a physician's clinical judgment.
- The HbA1c classification thresholds follow widely-used diabetes-society
  criteria (as a reasonably authoritative reference point); other tests use
  commonly-cited illustrative ranges and are explicitly flagged as such
  in-app and here.
- The application does not account for every clinical nuance (medications,
  pregnancy, comorbidities, population-specific variation, etc.).
- Not validated by a clinician; not a substitute for professional medical
  advice, diagnosis, or treatment.
- Session-based feedback only — nothing is persisted to a database.

## Future work

- Clinical review and validation of all thresholds and explanation text by
  a licensed physician.
- Expanded lab-test coverage and richer trend analysis over multiple visits.
- Formal accessibility and health-literacy testing with real (anonymized,
  consented) user feedback.
- Integration path into an actual HMO application, including the production
  security requirements listed above.

## Synthetic-data disclaimer

All patient names, ages, and clinical contexts throughout this application
— including all 12 demonstration scenarios — are entirely synthetic and
fictional. No real patient data was used at any stage of this project.

---

*This prototype is for educational demonstration only and is not a medical
device.*
