"""Detección de partidos finalizados (Betfair + Flashscore).

La señal principal de fin de partido es el marcador de sets:
- Grand Slam: mejor de 5 → gana quien llega a 3 sets
- Resto: mejor de 3 → gana quien llega a 2 sets

Si eso se cumple, el partido está terminado aunque el estado textual
siga diciendo "En juego" o Betfair aún no lo etiquete como CLOSED.
"""

from __future__ import annotations

from typing import Any

from flashscore_scraper.parser import is_finished_tennis_match

from collector.storage import FINISHED_STATUS
from tennisAgents.dataflows.market_resolve import set_is_complete

_GRAND_SLAM_KEYWORDS = (
    "wimbledon",
    "roland garros",
    "roland-garros",
    "roland garros",
    "french open",
    "us open",
    "u.s. open",
    "u.s.open",
    "australian open",
    "open de australia",
    "open australia",
    "grand slam",
)

_BEST_OF_THREE_OVERRIDES = (
    "qualif",
    "qualifier",
    "qualifying",
    "challenger",  # por si el nombre mezcla GS + challenger
)

_BETFAIR_FINISHED_STATUSES = frozenset(
    {
        "COMPLETE",
        "COMPLETED",
        "CLOSED",
        "ENDED",
        "FINISHED",
        "CANCELLED",
        "ABANDONED",
    }
)

_BETFAIR_LIVE_STATUSES = frozenset({"IN_RUNNING", "PRE_MATCH", "SCHEDULED"})


def sets_required_to_win(competition: str | None) -> int:
    """Sets necesarios para ganar el partido (3 en GS, 2 en el resto)."""
    comp = (competition or "").lower()
    if any(token in comp for token in _BEST_OF_THREE_OVERRIDES):
        return 2
    if any(keyword in comp for keyword in _GRAND_SLAM_KEYWORDS):
        return 3
    return 2


def _parse_sets_from_score(score: str | None) -> list[tuple[int, int]]:
    if not score:
        return []
    sets: list[tuple[int, int]] = []
    for part in score.split():
        if "-" not in part:
            continue
        left, _, right = part.partition("-")
        try:
            sets.append((int(left), int(right)))
        except ValueError:
            continue
    return sets


def sets_won_from_score(score: str | None) -> dict[str, int] | None:
    """Cuenta solo sets terminados; un 3-5 o 5-2 en curso no es set ganado."""
    p1 = p2 = 0
    for left, right in _parse_sets_from_score(score):
        if not set_is_complete(left, right):
            continue
        if left > right:
            p1 += 1
        elif right > left:
            p2 += 1
    if p1 == p2 == 0:
        return None
    return {"player1": p1, "player2": p2}


def _normalized_sets_won(sets_won: dict[str, Any] | None) -> dict[str, int] | None:
    if not isinstance(sets_won, dict):
        return None
    p1 = int(sets_won.get("player1") or 0)
    p2 = int(sets_won.get("player2") or 0)
    if p1 == 0 and p2 == 0:
        return None
    return {"player1": p1, "player2": p2}


def _sets_total(sets_won: dict[str, int] | None) -> int:
    if not sets_won:
        return 0
    return int(sets_won.get("player1") or 0) + int(sets_won.get("player2") or 0)


def has_decisive_match_winner(
    sets_won: dict[str, Any] | None,
    *,
    competition: str | None,
) -> bool:
    normalized = _normalized_sets_won(sets_won)
    if not normalized:
        return False
    needed = sets_required_to_win(competition)
    return normalized["player1"] >= needed or normalized["player2"] >= needed


def winner_side(
    sets_won: dict[str, Any] | None,
    *,
    competition: str | None,
) -> str | None:
    if not has_decisive_match_winner(sets_won, competition=competition):
        return None
    normalized = _normalized_sets_won(sets_won) or {"player1": 0, "player2": 0}
    if normalized["player1"] > normalized["player2"]:
        return "player1"
    if normalized["player2"] > normalized["player1"]:
        return "player2"
    return None


def status_is_finished(status: str | None) -> bool:
    if not status:
        return False
    lowered = status.lower()
    if any(token in lowered for token in FINISHED_STATUS):
        return True
    normalized = status.replace(" ", "_").upper()
    return normalized in _BETFAIR_FINISHED_STATUSES


def betfair_fixture_is_finished(fixture: dict[str, Any] | None) -> bool:
    if not fixture:
        return False
    match_status = (fixture.get("status") or {}).get("status")
    if not match_status:
        return False
    normalized = str(match_status).upper()
    if normalized in _BETFAIR_LIVE_STATUSES:
        return False
    return True


def resolve_sets_won(
    entry: dict[str, Any],
    fs_match: dict[str, Any] | None = None,
    *,
    prefer_fresh: bool = True,
) -> dict[str, int] | None:
    """
    Resuelve sets ganados.

    Un `sets_won` a 0-0 no bloquea el marcador textual: se deriva de los sets
    completos del score cuando aporta más información.
    """
    sources: list[dict[str, Any] | None] = []
    if prefer_fresh:
        sources.extend([fs_match, entry])
    else:
        sources.extend([entry, fs_match])

    candidates: list[dict[str, int]] = []
    for source in sources:
        if not source:
            continue
        normalized = _normalized_sets_won(source.get("sets_won"))
        if normalized:
            candidates.append(normalized)
        from_score = sets_won_from_score(source.get("score"))
        if from_score:
            candidates.append(from_score)

    live = entry.get("live_score") or {}
    live_sets = _normalized_sets_won(live.get("sets_won"))
    if live_sets:
        candidates.append(live_sets)
    live_from_score = sets_won_from_score(entry.get("score"))
    if live_from_score:
        candidates.append(live_from_score)

    if not candidates:
        return None

    # Preferir el conteo con más sets completos (evita 0-0 obsoleto).
    return max(candidates, key=_sets_total)


def entry_is_closed(entry: dict[str, Any]) -> bool:
    return bool(entry.get("finished_at") or entry.get("is_finished"))


def match_decided_by_sets(
    entry: dict[str, Any],
    fs_match: dict[str, Any] | None = None,
    *,
    score: str | None = None,
    competition: str | None = None,
) -> tuple[bool, dict[str, int] | None, str | None]:
    """True si el marcador de sets ya decide el partido (mejor de 3/5)."""
    comp = competition or entry.get("competition") or (
        (fs_match or {}).get("tournament") if fs_match else None
    )
    sets_won = resolve_sets_won(entry, fs_match, prefer_fresh=True)
    if score:
        from_score = sets_won_from_score(score)
        if _sets_total(from_score) > _sets_total(sets_won):
            sets_won = from_score
    if not has_decisive_match_winner(sets_won, competition=comp):
        return False, sets_won, None
    return True, sets_won, winner_side(sets_won, competition=comp)


def should_mark_finished(
    entry: dict[str, Any],
    *,
    in_betfair_live: bool,
    in_flashscore_live: bool,
    fs_match: dict[str, Any] | None = None,
    betfair_fixture: dict[str, Any] | None = None,
    betfair_unreachable: bool = False,
) -> bool:
    if entry_is_closed(entry):
        return True

    # 1) Señal primaria: sets decisivos (2 en ATP/WTA normal, 3 en Grand Slam).
    decided, _, _ = match_decided_by_sets(entry, fs_match)
    if decided:
        return True

    if status_is_finished(entry.get("status")):
        return True

    # Betfair CLOSED sin sets decisivos solo vale si Flashscore tampoco está live.
    if betfair_fixture_is_finished(betfair_fixture):
        if fs_match and is_finished_tennis_match(fs_match):
            return True
        if not in_flashscore_live and not (fs_match and fs_match.get("is_live")):
            return True
        return False

    if fs_match and is_finished_tennis_match(fs_match):
        if not fs_match.get("is_live") and fs_match.get("score"):
            return True

    if betfair_unreachable and not in_betfair_live and fs_match and not fs_match.get("is_live"):
        if is_finished_tennis_match(fs_match):
            return True

    if in_betfair_live or in_flashscore_live:
        return False

    if fs_match and not fs_match.get("is_live") and is_finished_tennis_match(fs_match):
        return True

    return False


def apply_finished_state(
    entry: dict[str, Any],
    *,
    now_iso: str,
    fs_match: dict[str, Any] | None = None,
    betfair_fixture: dict[str, Any] | None = None,
) -> None:
    entry["is_live"] = False
    entry["is_finished"] = True
    entry.setdefault("finished_at", now_iso)
    entry.pop("queued_for_snapshot", None)
    entry.pop("live_score", None)
    entry.pop("next_snapshot_at", None)

    if fs_match:
        if fs_match.get("score"):
            entry["score"] = fs_match["score"]
        entry["status"] = (
            fs_match["status"]
            if fs_match.get("status") and status_is_finished(fs_match.get("status"))
            else "Finalizado"
        )
    elif not status_is_finished(entry.get("status")):
        entry["status"] = "Finalizado"

    decided, sets_won, winner = match_decided_by_sets(entry, fs_match)
    if sets_won:
        entry["sets_won"] = sets_won
    if winner:
        entry["winner"] = winner
    elif decided:
        # Defensa: si hay sets decisivos, winner_side no debería fallar.
        entry["winner"] = winner_side(sets_won, competition=entry.get("competition"))

    if betfair_fixture_is_finished(betfair_fixture) and not decided:
        match_status = (betfair_fixture.get("status") or {}).get("status")
        if match_status:
            entry["status"] = str(match_status).replace("_", " ").title()
