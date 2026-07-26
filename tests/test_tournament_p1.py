"""Tests P1: contexto de analistas, informe verificado y settlement."""

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


if "tennisAgents.utils.enumerations" not in sys.modules:
    _load_module("tennisAgents.utils.enumerations", "tennisAgents/utils/enumerations.py")

if "tennisAgents.dataflows.config" not in sys.modules:
    config_stub = types.ModuleType("tennisAgents.dataflows.config")
    config_stub.get_config = lambda: {}
    sys.modules["tennisAgents.dataflows.config"] = config_stub

if "tennisAgents.dataflows.llm_utils" not in sys.modules:
    llm_stub = types.ModuleType("tennisAgents.dataflows.llm_utils")
    llm_stub.invoke_chat_llm = lambda *args, **kwargs: "WEB SEARCH SHOULD NOT RUN"
    llm_stub.invoke_local_analyst_llm = lambda *args, **kwargs: ("", "stub")
    sys.modules["tennisAgents.dataflows.llm_utils"] = llm_stub

if "tennisAgents.dataflows.web_search_utils" not in sys.modules:
    web_stub = types.ModuleType("tennisAgents.dataflows.web_search_utils")
    web_stub.perform_web_search = lambda *args, **kwargs: "WEB SEARCH SHOULD NOT RUN"
    sys.modules["tennisAgents.dataflows.web_search_utils"] = web_stub

tournament_utils = _load_module(
    "tennisAgents.dataflows.tournament_utils",
    "tennisAgents/dataflows/tournament_utils.py",
)

build_analyst_tournament_context = tournament_utils.build_analyst_tournament_context
get_tournament_info_openai = tournament_utils.get_tournament_info_openai
merge_analyst_tournament_context = tournament_utils.merge_analyst_tournament_context
STATE = sys.modules["tennisAgents.utils.enumerations"].STATE


class TournamentP1Tests(unittest.TestCase):
    def test_known_tournament_report_skips_web_search(self) -> None:
        report = get_tournament_info_openai("Tampere Challenger 2026", "ch", "2026-07-26")
        self.assertIn("Información verificada del torneo", report)
        self.assertIn("Tampere Open Challenger", report)
        self.assertIn("clay", report.lower())
        self.assertNotIn("WEB SEARCH SHOULD NOT RUN", report)

    def test_analyst_context_banner_includes_verified_surface(self) -> None:
        banner = build_analyst_tournament_context(
            "CHALLENGER MEN - SINGLES: Tampere (Finland), clay",
            betfair_competition="Tampere Challenger 2026",
        )
        self.assertIn("Superficie verificada: clay", banner)
        self.assertIn("Tampere Open Challenger", banner)

    def test_merge_analyst_context_prepends_banner(self) -> None:
        state = {
            STATE.tournament_context: "CONTEXTO VERIFICADO DEL TORNEO",
        }
        merged = merge_analyst_tournament_context(state, "Instrucciones del analista.")
        self.assertTrue(merged.startswith("CONTEXTO VERIFICADO DEL TORNEO"))
        self.assertIn("Instrucciones del analista.", merged)


if __name__ == "__main__":
    unittest.main()
