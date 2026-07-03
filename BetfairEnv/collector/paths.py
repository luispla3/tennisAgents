"""Rutas del proyecto y acceso a los scrapers externos."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RUN_DIR = ROOT / ".run"

# Repo tennisAgents: scrapers en tennisAgents/dataflows/
PROJECT_ROOT = ROOT.parent
SCRAPER_PATHS = (
    PROJECT_ROOT / "tennisAgents" / "dataflows",
    PROJECT_ROOT,
)

for path in SCRAPER_PATHS:
    path_str = str(path.resolve())
    while path_str in sys.path:
        sys.path.remove(path_str)
    sys.path.insert(0, path_str)
