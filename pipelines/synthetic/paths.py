"""Filesystem layout for synthetic remediation artifacts.

Code lives under pipelines/. Generated data and Power BI artifacts live at repo root.
Environment variables may override roots for isolated tests.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

_data_override = os.getenv("JAGA_DATA_ROOT") or os.getenv("JAGA_DATA_DIR")
DATA_ROOT = Path(_data_override) if _data_override else ROOT_DIR / "data" / "synthetic"
SCENARIO_DIR = DATA_ROOT / "scenario"
RAW_DIR = DATA_ROOT / "raw"
CURATED_DIR = DATA_ROOT / "curated"
CANDIDATE_ML_DIR = DATA_ROOT / "candidate_ml"

POWERBI_ROOT = Path(os.getenv("JAGA_POWERBI_DIR", ROOT_DIR / "powerbi"))
POWERBI_DATA_DIR = Path(os.getenv("JAGA_POWERBI_DATA_DIR", POWERBI_ROOT / "data"))
POWERBI_PARAMETER_DIR = POWERBI_ROOT / "parameters"


def ensure_output_dirs() -> None:
    for path in (
        SCENARIO_DIR,
        RAW_DIR,
        CURATED_DIR,
        CANDIDATE_ML_DIR,
        POWERBI_DATA_DIR,
        POWERBI_PARAMETER_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
