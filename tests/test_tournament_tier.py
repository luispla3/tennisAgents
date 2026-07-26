"""Tests de filtros de categoría de torneo."""

from __future__ import annotations

import importlib.util
import sys
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


_load_module(
    "tennisAgents.dataflows.tournament_calendar",
    "tennisAgents/dataflows/tournament_calendar.py",
)
tier = _load_module("tennisAgents.dataflows.tournament_tier", "tennisAgents/dataflows/tournament_tier.py")
filters = _load_module("tennisAgents.dataflows.match_filters", "tennisAgents/dataflows/match_filters.py")

is_tracked_tennis_match = filters.is_tracked_tennis_match
is_atp_challenger_or_higher_match = tier.is_atp_challenger_or_higher_match
matches_official_challenger_calendar = tier.matches_official_challenger_calendar
matches_official_atp_tour_calendar = tier.matches_official_atp_tour_calendar


class TournamentTierTests(unittest.TestCase):
    def test_accepts_grand_slam_and_atp_tour(self) -> None:
        for competition in (
            "Wimbledon",
            "ATP - SINGLES: Barcelona (Spain), clay",
            "Masters 1000 Miami",
            "Australian Open",
        ):
            with self.subTest(competition=competition):
                self.assertTrue(
                    is_atp_challenger_or_higher_match({"competition": competition})
                )

    def test_accepts_challenger_keyword(self) -> None:
        self.assertTrue(
            is_atp_challenger_or_higher_match(
                {"competition": "Challenger Men - Singles: Cordenons (Italy), clay"}
            )
        )
        self.assertTrue(
            is_atp_challenger_or_higher_match({"competition": "Challenger"})
        )

    def test_accepts_official_calendar_name(self) -> None:
        self.assertTrue(matches_official_challenger_calendar("Bengaluru Open"))
        self.assertTrue(
            is_atp_challenger_or_higher_match(
                {"competition": "CHALLENGER MEN - SINGLES: Bengaluru (India), hard"}
            )
        )

    def test_accepts_official_atp_tour_calendar_name(self) -> None:
        self.assertTrue(matches_official_atp_tour_calendar("Mutua Madrid Open"))
        self.assertTrue(
            is_atp_challenger_or_higher_match(
                {"competition": "Masters 1000: Rolex Monte-Carlo"}
            )
        )

    def test_rejects_itf_and_wta(self) -> None:
        for competition in (
            "ITF M25 Monastir",
            "ITF Men - Singles: Antalya",
            "WTA 250 Bogota",
            "ITF World Tennis Tour M15",
        ):
            with self.subTest(competition=competition):
                self.assertFalse(
                    is_atp_challenger_or_higher_match({"competition": competition})
                )

    def test_tracked_match_requires_singles_male_and_tier(self) -> None:
        self.assertTrue(
            is_tracked_tennis_match(
                {
                    "competition": "Challenger",
                    "player1": "Player A",
                    "player2": "Player B",
                }
            )
        )
        self.assertFalse(
            is_tracked_tennis_match(
                {
                    "competition": "ITF M25 Monastir",
                    "player1": "Player A",
                    "player2": "Player B",
                }
            )
        )
        self.assertFalse(
            is_tracked_tennis_match(
                {
                    "competition": "WTA 250",
                    "player1": "Player A",
                    "player2": "Player B",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
