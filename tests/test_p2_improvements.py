"""Tests P2: hora del partido, identidad de jugadores y sanitizado de informes."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

match_utils = importlib.util.module_from_spec(
    spec := importlib.util.spec_from_file_location(
        "tennisAgents.dataflows.match_utils",
        PROJECT_ROOT / "tennisAgents/dataflows/match_utils.py",
    )
)
assert spec.loader is not None
sys.modules["tennisAgents.dataflows.match_utils"] = match_utils
spec.loader.exec_module(match_utils)

report_utils = importlib.util.module_from_spec(
    spec2 := importlib.util.spec_from_file_location(
        "tennisAgents.agents.utils.report_utils",
        PROJECT_ROOT / "tennisAgents/agents/utils/report_utils.py",
    )
)
assert spec2.loader is not None
sys.modules["tennisAgents.agents.utils.report_utils"] = report_utils
spec2.loader.exec_module(report_utils)


class MatchUtilsTests(unittest.TestCase):
    def test_prefers_flashscore_start_time(self) -> None:
        resolved = match_utils.resolve_match_datetime(
            "2026-07-26",
            snapshot={
                "timestamp": "2026-07-26T08:36:57.503946+00:00",
                "flashscore": {
                    "match": {"start_time": "2026-07-26 11:30"},
                },
            },
        )
        self.assertEqual(resolved, "2026-07-26 11:30")

    def test_uses_snapshot_timestamp_when_no_start_time(self) -> None:
        resolved = match_utils.resolve_match_datetime(
            "2026-07-26",
            snapshot={"timestamp": "2026-07-26T08:36:57.503946+00:00"},
        )
        self.assertEqual(resolved, "2026-07-26 08:36")

    def test_falls_back_to_default_hour(self) -> None:
        resolved = match_utils.resolve_match_datetime("2026-07-26")
        self.assertEqual(resolved, "2026-07-26 14:00")


class ReportUtilsTests(unittest.TestCase):
    def test_removes_cjk_artifacts(self) -> None:
        cleaned = report_utils.sanitize_analyst_report(
            "Diferencia en熟悉idad con la superficie es marcada."
        )
        self.assertNotIn("熟悉", cleaned)
        self.assertIn("superficie", cleaned)


if __name__ == "__main__":
    unittest.main()
