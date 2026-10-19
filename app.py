#!/usr/bin/env python3
"""
BOOTSTRAP ENTRYPOINT FOR STREAMLIT INSPECTION APPLICATION
=========================================================
Pusat Gadai Indonesia (PGI) — Smartphone Defect Inspection, CIT & Valuation Platform

Canonical Entry Point: Launches the enterprise application from streamlit_inspection_app/app.py.
Eliminates code duplication and ensures single-source-of-truth across environments.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
APP_SCRIPT = BASE_DIR / "streamlit_inspection_app" / "app.py"

# Ensure root repository and streamlit_inspection_app directories are on path
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

app_dir = str(BASE_DIR / "streamlit_inspection_app")
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

if __name__ == "__main__":
    import runpy
    os.chdir(str(BASE_DIR))
    runpy.run_path(str(APP_SCRIPT), run_name="__main__")
