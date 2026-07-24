"""Fusión robusta de marcador Flashscore + live_score Betfair.

Flashscore scoreboard es la base. Betfair solo enriquece cuando su live
no está por detrás (evita pisar un 6-4 real con un 0-0 stale).
"""

from __future__ import annotations

from typing import Any

import collector.paths  # noqa: F401
from tennisAgents.dataflows.market_resolve import derive_sets_won, set_is_complete
from flashscore_scraper.parser import (
    AWAY_SETS_WON,
    HOME_SETS_WON,
    _format_score,
)


def parse_sets_detail(score: str | None) -> list[dict[str, int]]:
    if not score:
        return []
    sets: list[dict[str, int]] = []
    for part in score.split():
        if "-" not in part:
            continue
        left, _, right = part.partition("-")
        try:
            sets.append({"player1": int(left), "player2": int(right)})
        except ValueError:
            continue
    return sets


def sets_won_total(sets_won: dict[str, Any] | None) -> int:
    if not isinstance(sets_won, dict):
        return 0
    return int(sets_won.get("player1") or 0) + int(sets_won.get("player2") or 0)


def sets_detail_games(sets_detail: list[dict[str, int]] | None) -> int:
    total = 0
    for item in sets_detail or []:
        total += int(item.get("player1") or 0) + int(item.get("player2") or 0)
    return total


def sanitize_sets_detail(
    sets_detail: list[dict[str, int]] | None,
) -> list[dict[str, int]]:
    """Quita placeholders 0-0 a la cabeza cuando ya hay sets posteriores reales."""
    detail = [
        {
            "player1": int(item.get("player1") or 0),
            "player2": int(item.get("player2") or 0),
        }
        for item in (sets_detail or [])
    ]
    while len(detail) >= 2:
        first = detail[0]
        if first["player1"] == 0 and first["player2"] == 0:
            detail.pop(0)
            continue
        break
    return detail


def score_from_sets_detail(sets_detail: list[dict[str, int]] | None) -> str | None:
    detail = sanitize_sets_detail(sets_detail)
    if not detail:
        return None
    return " ".join(f"{item['player1']}-{item['player2']}" for item in detail)


def refresh_score_fields(section: dict[str, Any]) -> None:
    detail = sanitize_sets_detail(
        section.get("sets_detail") or parse_sets_detail(section.get("score"))
    )
    if detail:
        section["sets_detail"] = detail
        section["score"] = score_from_sets_detail(detail)
    derived = derive_sets_won(detail)
    existing = section.get("sets_won")
    if sets_won_total(derived) > sets_won_total(existing):
        section["sets_won"] = derived
    elif existing is None and sets_won_total(derived) > 0:
        section["sets_won"] = derived
    sets_won = section.get("sets_won") or {}
    p1 = sets_won.get("player1")
    p2 = sets_won.get("player2")
    if p1 is not None and p2 is not None and int(p1) != int(p2):
        section["leading"] = "player1" if int(p1) > int(p2) else "player2"


def apply_scoreboard_raw(section: dict[str, Any], raw: dict[str, str]) -> None:
    score = _format_score(raw)
    if score:
        section["score"] = score
        section["sets_detail"] = parse_sets_detail(score)
    raw_sets = None
    if HOME_SETS_WON in raw or AWAY_SETS_WON in raw:
        raw_sets = {
            "player1": int(raw.get(HOME_SETS_WON, "0") or "0"),
            "player2": int(raw.get(AWAY_SETS_WON, "0") or "0"),
        }
    derived = derive_sets_won(section.get("sets_detail"))
    if raw_sets and sets_won_total(raw_sets) >= sets_won_total(derived):
        section["sets_won"] = raw_sets
    elif sets_won_total(derived) > 0:
        section["sets_won"] = derived
    refresh_score_fields(section)


def betfair_live_is_ahead_or_equal(
    *,
    existing_detail: list[dict[str, int]],
    existing_set_wins: int,
    bf_set_wins: int,
    bf_games_in_set: int,
) -> bool:
    """True si el live de Betfair no está por detrás del marcador Flashscore."""
    existing_games = sets_detail_games(existing_detail)
    if existing_games > 0 and bf_set_wins == 0 and bf_games_in_set == 0:
        return False
    if bf_set_wins > existing_set_wins:
        return True
    if bf_set_wins < existing_set_wins:
        return False
    if not existing_detail:
        return bf_set_wins > 0 or bf_games_in_set > 0
    idx = bf_set_wins
    if idx < len(existing_detail):
        current = existing_detail[idx]
        existing_current_games = int(current.get("player1") or 0) + int(
            current.get("player2") or 0
        )
        if set_is_complete(
            int(current.get("player1") or 0),
            int(current.get("player2") or 0),
        ):
            return False
        return bf_games_in_set >= existing_current_games
    return bf_games_in_set > 0


def merge_betfair_live_score(
    section: dict[str, Any],
    live_score: dict[str, Any] | None,
) -> None:
    """
    Enriquece el marcador con Betfair solo cuando aporta progreso real.

    Flashscore scoreboard es la base. Un live_score Betfair stale (0-0 eterno)
    no puede machacar sets/juegos ya conocidos.
    """
    if not live_score:
        return

    existing_detail = sanitize_sets_detail(
        section.get("sets_detail") or parse_sets_detail(section.get("score"))
    )
    existing_sets_won = section.get("sets_won") or derive_sets_won(existing_detail)
    existing_set_wins = max(
        sets_won_total(existing_sets_won),
        sets_won_total(derive_sets_won(existing_detail)),
    )

    bf_sets_won_raw = live_score.get("sets_won")
    bf_set_wins = sets_won_total(bf_sets_won_raw)
    current_set = live_score.get("current_set") or {}
    try:
        bf_p1 = (
            int(current_set.get("player1"))
            if current_set.get("player1") is not None
            else None
        )
        bf_p2 = (
            int(current_set.get("player2"))
            if current_set.get("player2") is not None
            else None
        )
    except (TypeError, ValueError):
        bf_p1 = bf_p2 = None
    bf_games_in_set = (
        (bf_p1 or 0) + (bf_p2 or 0) if bf_p1 is not None and bf_p2 is not None else 0
    )

    score_usable = betfair_live_is_ahead_or_equal(
        existing_detail=existing_detail,
        existing_set_wins=existing_set_wins,
        bf_set_wins=bf_set_wins,
        bf_games_in_set=bf_games_in_set,
    )

    if score_usable and bf_sets_won_raw and bf_set_wins >= existing_set_wins:
        section["sets_won"] = {
            "player1": int(bf_sets_won_raw.get("player1") or 0),
            "player2": int(bf_sets_won_raw.get("player2") or 0),
        }

    if score_usable and bf_p1 is not None and bf_p2 is not None:
        sets_won = section.get("sets_won") or existing_sets_won or {}
        p1_sets = int(sets_won.get("player1") or 0)
        p2_sets = int(sets_won.get("player2") or 0)
        set_index = p1_sets + p2_sets
        sets_detail = list(existing_detail)
        entry = {"player1": bf_p1, "player2": bf_p2}
        if set_index < len(sets_detail):
            sets_detail[set_index] = entry
        elif set_index == len(sets_detail):
            sets_detail.append(entry)
        if sets_detail:
            section["sets_detail"] = sets_detail
            section["current_game"] = {"player1": bf_p1, "player2": bf_p2}

    if score_usable or sets_detail_games(existing_detail) == 0:
        current_game = live_score.get("current_game")
        if current_game:
            section["current_points"] = {
                "player1": str(current_game.get("player1", "")),
                "player2": str(current_game.get("player2", "")),
            }
        if live_score.get("serving"):
            section["serving"] = live_score["serving"]

    refresh_score_fields(section)


def score_label(entry: dict[str, Any]) -> str | None:
    live = entry.get("live_score") or {}
    sets_won = live.get("sets_won") or {}
    current = live.get("current_set")
    base_detail = sanitize_sets_detail(parse_sets_detail(entry.get("score")))
    if current and current.get("player1") is not None and current.get("player2") is not None:
        try:
            bf_p1 = int(current["player1"])
            bf_p2 = int(current["player2"])
        except (TypeError, ValueError):
            return score_from_sets_detail(base_detail) or entry.get("score")
        p1_sets = int(sets_won.get("player1") or 0)
        p2_sets = int(sets_won.get("player2") or 0)
        usable = betfair_live_is_ahead_or_equal(
            existing_detail=base_detail,
            existing_set_wins=max(
                p1_sets + p2_sets,
                sets_won_total(derive_sets_won(base_detail)),
            ),
            bf_set_wins=p1_sets + p2_sets,
            bf_games_in_set=bf_p1 + bf_p2,
        )
        if not usable:
            return score_from_sets_detail(base_detail) or entry.get("score")
        parts = [f"{item['player1']}-{item['player2']}" for item in base_detail]
        set_index = p1_sets + p2_sets
        current_part = f"{bf_p1}-{bf_p2}"
        if set_index < len(parts):
            parts[set_index] = current_part
        elif set_index == len(parts):
            parts.append(current_part)
        if parts:
            return " ".join(parts)
    return score_from_sets_detail(base_detail) or entry.get("score")


def build_flashscore_section(
    fs_match: dict[str, Any],
    stats: dict[str, Any] | None,
    scoreboard_raw: dict[str, str] | None,
    *,
    live_score: dict[str, Any] | None = None,
    stats_error: str | None = None,
    scoreboard_error: str | None = None,
    winner_side: str | None = None,
) -> dict[str, Any]:
    """Construye la sección flashscore del snapshot con merge seguro."""
    sets_won = fs_match.get("sets_won") or {}
    leading = None
    p1 = sets_won.get("player1")
    p2 = sets_won.get("player2")
    if p1 is not None and p2 is not None and p1 != p2:
        leading = "player1" if p1 > p2 else "player2"

    section: dict[str, Any] = {
        "score": fs_match.get("score"),
        "sets_won": sets_won or None,
        "sets_detail": parse_sets_detail(fs_match.get("score")),
        "leading": leading,
        "winner": winner_side,
        "match": {
            "id": fs_match.get("id"),
            "status": fs_match.get("status"),
            "tournament": fs_match.get("tournament"),
        },
    }
    if scoreboard_raw:
        section["scoreboard_raw"] = scoreboard_raw
        apply_scoreboard_raw(section, scoreboard_raw)
    merge_betfair_live_score(section, live_score)
    refresh_score_fields(section)
    if stats:
        section["statistics"] = {
            "overall": stats.get("overall") or {},
            "periods": stats.get("periods") or [],
        }
    if stats_error:
        section["statistics_error"] = stats_error
    if scoreboard_error:
        section["scoreboard_error"] = scoreboard_error
    return section
