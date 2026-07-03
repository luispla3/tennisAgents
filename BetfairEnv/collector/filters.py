"""Filtros de partidos de tenis (singles masculino)."""

from __future__ import annotations

import re
from typing import Any

_WOMENS_KEYWORDS = (
    "femenin",
    "women",
    "wta",
    "ladies",
    "damen",
    " fem ",
    "(w)",
    " fem.",
)
_DOUBLES_KEYWORDS = (
    "dobles",
    "double",
    "mixed",
    "mixto",
)


def _text(*values: Any) -> str:
    return " ".join(str(v) for v in values if v).lower()


def _looks_like_doubles(match: dict[str, Any]) -> bool:
    for key in ("player1", "player2", "name"):
        value = str(match.get(key) or "")
        if "/" in value:
            return True
    blob = _text(match.get("competition"), match.get("tournament"), match.get("category"), match.get("name"))
    return any(token in blob for token in _DOUBLES_KEYWORDS)


def _looks_like_womens(match: dict[str, Any]) -> bool:
    blob = _text(
        match.get("competition"),
        match.get("tournament"),
        match.get("category"),
        match.get("name"),
    )
    if any(token in blob for token in _WOMENS_KEYWORDS):
        return True
    return bool(re.search(r"\bw\b", blob))


def is_singles_male_tennis_match(match: dict[str, Any]) -> bool:
    """True si el partido parece singles masculino de tenis."""
    if not match.get("player1") or not match.get("player2"):
        return False
    if _looks_like_doubles(match):
        return False
    if _looks_like_womens(match):
        return False
    return True


def filter_betfair_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [m for m in matches if is_singles_male_tennis_match(m)]


def filter_flashscore_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [m for m in matches if is_singles_male_tennis_match(m)]
