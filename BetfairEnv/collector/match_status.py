"""Detección de partidos finalizados (Betfair + Flashscore)."""

from __future__ import annotations

from typing import Any

from flashscore_scraper.parser import is_finished_tennis_match

from collector.storage import FINISHED_STATUS

_GRAND_SLAM_KEYWORDS = (
    "wimbledon",
    "roland garros",
    "roland-garros",
    "french open",
    "us open",
    "australian open",
    "grand slam",
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
    comp = (competition or "").lower()
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
    p1 = p2 = 0
    for left, right in _parse_sets_from_score(score):
        if left > right:
            p1 += 1
        elif right > left:
            p2 += 1
    if p1 == p2 == 0:
        return None
    return {"player1": p1, "player2": p2}


def has_decisive_match_winner(
    sets_won: dict[str, Any] | None,
    *,
    competition: str | None,
) -> bool:
    if not sets_won:
        return False
    needed = sets_required_to_win(competition)
    p1 = int(sets_won.get("player1") or 0)
    p2 = int(sets_won.get("player2") or 0)
    return p1 >= needed or p2 >= needed


def winner_side(
    sets_won: dict[str, Any] | None,
    *,
    competition: str | None,
) -> str | None:
    if not has_decisive_match_winner(sets_won, competition=competition):
        return None
    p1 = int(sets_won.get("player1") or 0)
    p2 = int(sets_won.get("player2") or 0)
    if p1 > p2:
        return "player1"
    if p2 > p1:
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
    """Resuelve sets ganados priorizando datos frescos del feed diario."""
    sources: list[dict[str, Any] | None] = []
    if prefer_fresh:
        sources.extend([fs_match, entry])
    else:
        sources.extend([entry, fs_match])

    for source in sources:
        if not source:
            continue
        if source.get("sets_won"):
            return source["sets_won"]
        from_score = sets_won_from_score(source.get("score"))
        if from_score:
            return from_score

    live = entry.get("live_score") or {}
    if live.get("sets_won"):
        return live["sets_won"]
    return sets_won_from_score(entry.get("score"))


def entry_is_closed(entry: dict[str, Any]) -> bool:
    return bool(entry.get("finished_at") or entry.get("is_finished"))


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
    if status_is_finished(entry.get("status")):
        return True
    if betfair_fixture_is_finished(betfair_fixture):
        return True

    competition = entry.get("competition")
    sets_won = resolve_sets_won(entry, fs_match, prefer_fresh=True)

    # Ganador definitivo por sets: manda sobre flags is_live desactualizados.
    if has_decisive_match_winner(sets_won, competition=competition):
        return True

    if fs_match and is_finished_tennis_match(fs_match):
        fresh_sets = resolve_sets_won(entry, fs_match, prefer_fresh=True)
        if has_decisive_match_winner(fresh_sets, competition=competition):
            return True
        if not fs_match.get("is_live") and fs_match.get("score"):
            return True

    # Desapareció de Betfair en vivo y ya no responde: confiar en Flashscore diario.
    if betfair_unreachable and not in_betfair_live and fs_match and not fs_match.get("is_live"):
        if is_finished_tennis_match(fs_match) or has_decisive_match_winner(
            resolve_sets_won(entry, fs_match, prefer_fresh=True),
            competition=competition,
        ):
            return True

    # Sin listas en vivo ni ganador claro: no marcar todavía.
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
        if fs_match.get("sets_won"):
            entry["sets_won"] = fs_match["sets_won"]
        entry["status"] = (
            fs_match["status"]
            if fs_match.get("status") and status_is_finished(fs_match.get("status"))
            else "Finalizado"
        )
    elif not status_is_finished(entry.get("status")):
        entry["status"] = "Finalizado"

    sets_won = resolve_sets_won(entry, fs_match, prefer_fresh=True)
    winner = winner_side(sets_won, competition=entry.get("competition"))
    if winner:
        entry["winner"] = winner

    if betfair_fixture_is_finished(betfair_fixture):
        match_status = (betfair_fixture.get("status") or {}).get("status")
        if match_status:
            entry["status"] = str(match_status).replace("_", " ").title()
