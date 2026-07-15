"""Filtros de partidos de tenis (singles masculino)."""

from __future__ import annotations

from typing import Any

from tennisAgents.dataflows.match_filters import (
    filter_singles_male_matches,
    is_singles_male_tennis_match,
)


def filter_betfair_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return filter_singles_male_matches(matches)


def filter_flashscore_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return filter_singles_male_matches(matches)
