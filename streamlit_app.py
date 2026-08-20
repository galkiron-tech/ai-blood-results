"""
streamlit_app.py

Deployment entry point for Streamlit Community Cloud, which by convention
looks for a file named `streamlit_app.py` in the repository root.

This file intentionally contains no logic of its own - it simply runs the
same `main()` function used by the canonical entry point, `app.py`
(for local development: `streamlit run app.py`), so there is a single
source of truth for the application.
"""

from app import main

main()
