"""Tests de integración de calendarios oficiales con normalización y clima."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_module(name: str, rel_path: str):
    path = PROJECT_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


calendar = _load_module(
    "tennisAgents.dataflows.tournament_calendar",
    "tennisAgents/dataflows/tournament_calendar.py",
)

if "tennisAgents.dataflows.config" not in sys.modules:
    config_stub = types.ModuleType("tennisAgents.dataflows.config")
    config_stub.get_config = lambda: {}
    sys.modules["tennisAgents.dataflows.config"] = config_stub

if "tennisAgents.dataflows.llm_utils" not in sys.modules:
    llm_stub = types.ModuleType("tennisAgents.dataflows.llm_utils")
    llm_stub.invoke_chat_llm = lambda *args, **kwargs: ""
    llm_stub.invoke_local_analyst_llm = lambda *args, **kwargs: ("", "stub")
    sys.modules["tennisAgents.dataflows.llm_utils"] = llm_stub

if "tennisAgents.dataflows.web_search_utils" not in sys.modules:
    web_stub = types.ModuleType("tennisAgents.dataflows.web_search_utils")
    web_stub.perform_web_search = lambda *args, **kwargs: ""
    sys.modules["tennisAgents.dataflows.web_search_utils"] = web_stub

tournament_utils = _load_module(
    "tennisAgents.dataflows.tournament_utils",
    "tennisAgents/dataflows/tournament_utils.py",
)

find_official_tournament = calendar.find_official_tournament
locations_match = calendar.locations_match
normalize_tournament = tournament_utils.normalize_tournament
resolve_weather_location = tournament_utils.resolve_weather_location


class TournamentCalendarIntegrationTests(unittest.TestCase):
    def test_challenger_calendar_enriches_cordenons(self) -> None:
        identity = normalize_tournament("CHALLENGER MEN - SINGLES: Cordenons (Italy), clay")
        self.assertEqual(identity.official_name, "Cordenons Challenger")
        self.assertEqual(identity.location, "Cordenons, Italy")
        self.assertEqual(identity.calendar_source, "challenger")
        self.assertTrue(identity.location_verified)

    def test_atp_tour_calendar_enriches_gstaad(self) -> None:
        identity = normalize_tournament("ATP 250 - Gstaad (Switzerland), clay")
        self.assertEqual(identity.official_name, "Swiss Open Gstaad")
        self.assertEqual(identity.location, "Gstaad, Switzerland")
        self.assertEqual(identity.calendar_source, "atp_tour")

    def test_weather_location_prefers_official_calendar(self) -> None:
        resolved, verified, note = resolve_weather_location(
            "CHALLENGER MEN - SINGLES: Cordenons (Italy), clay",
            "Wrong City, Italy",
        )
        self.assertEqual(resolved, "Cordenons, Italy")
        self.assertFalse(verified)
        self.assertIn("no coincide", note or "")

    def test_weather_location_verified_when_matches(self) -> None:
        resolved, verified, note = resolve_weather_location(
            "Swiss Open Gstaad",
            "Gstaad, Switzerland",
        )
        self.assertEqual(resolved, "Gstaad, Switzerland")
        self.assertTrue(verified)
        self.assertIsNone(note)

    def test_locations_match_by_city(self) -> None:
        self.assertTrue(locations_match("Cordenons (Italy)", "Cordenons, Italy"))
        self.assertFalse(locations_match("Paris, France", "Lyon, France"))


if __name__ == "__main__":
    unittest.main()
