"""Emparejamiento Betfair ↔ Flashscore por nombres de jugadores."""

from __future__ import annotations

import unicodedata
from typing import Any


def normalize_name(name: str) -> str:
    text = unicodedata.normalize("NFD", name or "")
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return " ".join(text.lower().split())


def _name_parts(name: str) -> list[str]:
    normalized = normalize_name(name)
    if "," in normalized:
        left, _, right = normalized.partition(",")
        parts = [left.strip(), right.strip()]
    else:
        parts = normalized.split()
    return [p for p in parts if len(p) >= 2]


def _player_hits(part: str, candidates: list[str]) -> bool:
    if not part:
        return False
    for candidate in candidates:
        if part in candidate or candidate in part:
            return True
    return False


def match_score(betfair_match: dict[str, Any], flashscore_match: dict[str, Any]) -> int:
    """Puntuación de coincidencia (mayor = mejor)."""
    fs_names = [
        normalize_name(flashscore_match.get("player1", "")),
        normalize_name(flashscore_match.get("player2", "")),
    ]

    score = 0
    for side in ("player1", "player2"):
        for part in _name_parts(str(betfair_match.get(side) or "")):
            if _player_hits(part, fs_names):
                score += 10 if part == _name_parts(str(betfair_match.get(side) or ""))[-1] else 5

    comp_bf = normalize_name(betfair_match.get("competition", ""))
    comp_fs = normalize_name(flashscore_match.get("tournament", ""))
    if comp_bf and comp_fs and (comp_bf in comp_fs or comp_fs in comp_bf):
        score += 3

    return score


def find_flashscore_match(
    betfair_match: dict[str, Any],
    flashscore_matches: list[dict[str, Any]],
    *,
    min_score: int = 10,
) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_score = 0
    for candidate in flashscore_matches:
        score = match_score(betfair_match, candidate)
        if score > best_score:
            best_score = score
            best = candidate
    if best_score < min_score:
        return None
    return best
