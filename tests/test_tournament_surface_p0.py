"""Tests P0: superficie, calendario y prioridad de fuentes."""

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

normalize_tournament = tournament_utils.normalize_tournament
resolve_tournament_raw = tournament_utils.resolve_tournament_raw
resolve_tournament_identity = tournament_utils.resolve_tournament_identity
_lookup_surface_from_text = tournament_utils._lookup_surface_from_text
find_official_tournament = calendar.find_official_tournament


class TournamentSurfaceP0Tests(unittest.TestCase):
    def test_challenger_does_not_infer_grass_from_halle(self) -> None:
        self.assertIsNone(_lookup_surface_from_text("Tampere Challenger 2026"))
        identity = normalize_tournament("Tampere Challenger 2026")
        self.assertNotEqual(identity.surface, "grass")

    def test_tampere_resolves_via_official_calendar(self) -> None:
        identity = normalize_tournament("Tampere Challenger 2026")
        self.assertEqual(identity.official_name, "Tampere Open Challenger")
        self.assertEqual(identity.location, "Tampere, Finland")
        self.assertEqual(identity.surface, "clay")
        self.assertEqual(identity.calendar_source, "challenger")

    def test_flashscore_format_explicit_clay(self) -> None:
        raw = "CHALLENGER MEN - SINGLES: Tampere (Finland), clay"
        identity = normalize_tournament(raw)
        self.assertEqual(identity.surface, "clay")
        self.assertEqual(identity.official_name, "Tampere Open Challenger")

    def test_resolve_tournament_raw_prefers_flashscore_over_betfair(self) -> None:
        resolved = resolve_tournament_raw(
            betfair_competition="Tampere Challenger 2026",
            flashscore_tournament="CHALLENGER MEN - SINGLES: Tampere (Finland), clay",
        )
        self.assertIn("clay", resolved.lower())
        identity = normalize_tournament(resolved)
        self.assertEqual(identity.surface, "clay")

    def test_halle_still_matches_real_halle_tournament(self) -> None:
        self.assertEqual(_lookup_surface_from_text("ATP 500 Halle"), "grass")

    def test_find_official_tournament_by_city_key(self) -> None:
        official = find_official_tournament("Tampere 2026")
        self.assertIsNotNone(official)
        assert official is not None
        self.assertEqual(official.name, "Tampere Open Challenger")

    def test_resolve_identity_prefers_flashscore_clay_over_betfair(self) -> None:
        identity = resolve_tournament_identity(
            betfair_competition="San Marino Challenger 2026",
            flashscore_tournament="CHALLENGER MEN - SINGLES: San Marino (San Marino), clay",
        )
        self.assertEqual(identity.surface, "clay")
        self.assertIn("clay", identity.display_name)

    def test_known_challenger_without_flashscore_uses_local_knowledge(self) -> None:
        identity = resolve_tournament_identity(
            betfair_competition="San Marino Challenger 2026",
        )
        self.assertEqual(identity.surface, "clay")
        self.assertIn("San Marino", identity.location or "")


if __name__ == "__main__":
    unittest.main()
