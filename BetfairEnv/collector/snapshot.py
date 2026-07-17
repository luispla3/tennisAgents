"""Captura de snapshots Betfair + Flashscore."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import collector.paths  # noqa: F401

from collector.anti_block import pause_between_requests, pause_between_sources
from collector.config import DEFAULT_LOCALE, DEFAULT_SPORT, TRACK_GRACE_MINUTES
from collector.filters import filter_betfair_matches, filter_flashscore_matches
from collector.matcher import find_flashscore_match
from collector.match_status import (
    apply_finished_state,
    entry_is_closed,
    should_mark_finished,
    status_is_finished,
)
from collector.storage import (
    _parse_iso,
    _utc_now_iso,
    effective_is_live,
    is_snapshot_due,
    load_index,
    save_index,
    save_snapshot,
    schedule_next_snapshot,
)
from betfair_scraper.client import BetfairClient, BetfairError
from betfair_scraper.graphql import GraphQLClient, event_view_urn
from betfair_scraper.parser import iter_nodes_by_type
from betfair_scraper.scraper import get_event_markets, get_live_matches
from flashscore_scraper import get_live_matches as fs_get_live_matches
from flashscore_scraper import get_match_statistics, get_matches as fs_get_matches
from flashscore_scraper.client import FlashscoreClient, FlashscoreError
from flashscore_scraper.parser import (
    AWAY_SETS_WON,
    HOME_SETS_WON,
    _format_score,
    parse_scoreboard_feed,
)

log = logging.getLogger("collector.snapshot")


def _parse_sets_detail(score: str | None) -> list[dict[str, int]]:
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


def _side_from_winner(winner_name: str | None, player1: str, player2: str) -> str | None:
    if not winner_name:
        return None
    from collector.matcher import normalize_name

    winner = normalize_name(winner_name)
    if winner == normalize_name(player1):
        return "player1"
    if winner == normalize_name(player2):
        return "player2"
    return None


def _apply_scoreboard_raw(section: dict[str, Any], raw: dict[str, str]) -> None:
    score = _format_score(raw)
    if score:
        section["score"] = score
        section["sets_detail"] = _parse_sets_detail(score)
    if HOME_SETS_WON in raw or AWAY_SETS_WON in raw:
        section["sets_won"] = {
            "player1": int(raw.get(HOME_SETS_WON, "0") or "0"),
            "player2": int(raw.get(AWAY_SETS_WON, "0") or "0"),
        }


def _merge_betfair_live_score(section: dict[str, Any], live_score: dict[str, Any] | None) -> None:
    """Prioriza el marcador en vivo de Betfair sobre el feed diario de Flashscore."""
    if not live_score:
        return

    sets_won = live_score.get("sets_won")
    if sets_won:
        section["sets_won"] = sets_won
        p1 = sets_won.get("player1")
        p2 = sets_won.get("player2")
        if p1 is not None and p2 is not None and p1 != p2:
            section["leading"] = "player1" if p1 > p2 else "player2"

    current_set = live_score.get("current_set")
    if current_set and current_set.get("player1") is not None and current_set.get("player2") is not None:
        section["current_game"] = {
            "player1": int(current_set["player1"]),
            "player2": int(current_set["player2"]),
        }
        sets_detail = list(section.get("sets_detail") or [])
        p1_sets = int((sets_won or section.get("sets_won") or {}).get("player1") or 0)
        p2_sets = int((sets_won or section.get("sets_won") or {}).get("player2") or 0)
        set_index = p1_sets + p2_sets
        entry = {
            "player1": int(current_set["player1"]),
            "player2": int(current_set["player2"]),
        }
        if set_index < len(sets_detail):
            sets_detail[set_index] = entry
        elif set_index == len(sets_detail):
            sets_detail.append(entry)
        else:
            while len(sets_detail) < set_index:
                sets_detail.append({"player1": 0, "player2": 0})
            sets_detail.append(entry)
        section["sets_detail"] = sets_detail
        section["score"] = " ".join(f"{s['player1']}-{s['player2']}" for s in sets_detail)

    current_game = live_score.get("current_game")
    if current_game:
        section["current_points"] = {
            "player1": str(current_game.get("player1", "")),
            "player2": str(current_game.get("player2", "")),
        }
    if live_score.get("serving"):
        section["serving"] = live_score["serving"]


def _score_label(entry: dict[str, Any]) -> str | None:
    live = entry.get("live_score") or {}
    sets_won = live.get("sets_won") or {}
    current = live.get("current_set")
    if current and current.get("player1") is not None and current.get("player2") is not None:
        prefix = entry.get("score") or ""
        parts = prefix.split() if prefix else []
        p1_sets = int(sets_won.get("player1") or 0)
        p2_sets = int(sets_won.get("player2") or 0)
        set_index = p1_sets + p2_sets
        current_part = f"{current['player1']}-{current['player2']}"
        if set_index < len(parts):
            parts[set_index] = current_part
        elif set_index == len(parts):
            parts.append(current_part)
        if parts:
            return " ".join(parts)
    return entry.get("score")


def _build_betfair_section(event_data: dict[str, Any], betfair_match: dict[str, Any]) -> dict[str, Any]:
    event = event_data.get("event") or betfair_match
    markets = event_data.get("markets") or []
    primary = event.get("primary_market")
    if not primary:
        primary = next((m for m in markets if m.get("market_type") == "MATCH_ODDS"), None)
    live_score = event.get("live_score") or betfair_match.get("live_score")
    return {
        "status": event.get("status") or betfair_match.get("status"),
        "is_live": bool(event.get("is_live", betfair_match.get("is_live"))),
        "player1": event.get("player1") or betfair_match.get("player1"),
        "player2": event.get("player2") or betfair_match.get("player2"),
        "competition": event.get("competition") or betfair_match.get("competition"),
        "primary_market": primary,
        "markets": markets,
        "live_score": live_score,
    }


def _build_flashscore_section(
    fs_match: dict[str, Any],
    stats: dict[str, Any] | None,
    scoreboard_raw: dict[str, str] | None,
    *,
    live_score: dict[str, Any] | None = None,
    stats_error: str | None = None,
) -> dict[str, Any]:
    player1 = fs_match.get("player1", "")
    player2 = fs_match.get("player2", "")
    sets_won = fs_match.get("sets_won") or {}
    winner_name = fs_match.get("winner")
    leading = None
    p1 = sets_won.get("player1")
    p2 = sets_won.get("player2")
    if p1 is not None and p2 is not None and p1 != p2:
        leading = "player1" if p1 > p2 else "player2"

    section: dict[str, Any] = {
        "score": fs_match.get("score"),
        "sets_won": sets_won or None,
        "sets_detail": _parse_sets_detail(fs_match.get("score")),
        "leading": leading,
        "winner": _side_from_winner(winner_name, player1, player2),
        "match": {
            "id": fs_match.get("id"),
            "status": fs_match.get("status"),
            "tournament": fs_match.get("tournament"),
        },
    }
    if scoreboard_raw:
        section["scoreboard_raw"] = scoreboard_raw
        _apply_scoreboard_raw(section, scoreboard_raw)
    _merge_betfair_live_score(section, live_score)
    if stats:
        section["statistics"] = {
            "overall": stats.get("overall") or {},
            "periods": stats.get("periods") or [],
        }
    if stats_error:
        section["statistics_error"] = stats_error
    return section


def _fresh_flashscore_match(match_id: str, *, sport: str, locale: str) -> dict[str, Any] | None:
    try:
        live = filter_flashscore_matches(fs_get_live_matches(sport, locale=locale))
    except FlashscoreError:
        return None
    for match in live:
        if str(match.get("id")) == str(match_id):
            return match
    return None


def _fetch_flashscore_enrichment(match_id: str, locale: str) -> tuple[dict[str, Any] | None, dict[str, str] | None, str | None]:
    stats: dict[str, Any] | None = None
    scoreboard_raw: dict[str, str] | None = None
    stats_error: str | None = None

    try:
        stats = get_match_statistics(match_id, locale=locale)
    except FlashscoreError as exc:
        stats_error = str(exc)

    try:
        client = FlashscoreClient(locale=locale)
        raw = client.get_match_scoreboard(match_id)
        scoreboard_raw = parse_scoreboard_feed(raw)
    except FlashscoreError:
        pass

    return stats, scoreboard_raw, stats_error


def _capture_snapshot(
    event_id: str,
    entry: dict[str, Any],
    betfair_match: dict[str, Any] | None,
    fs_match: dict[str, Any] | None,
    *,
    sport: str,
    locale: str,
) -> dict[str, Any]:
    event_id_int = int(entry.get("betfair_event_id") or event_id)
    pause_between_requests()
    event_data = get_event_markets(event_id_int, sport=sport)

    fs_data = fs_match
    if fs_data is None and entry.get("flashscore_match_id"):
        fs_data = {
            "id": entry["flashscore_match_id"],
            "player1": entry.get("player1"),
            "player2": entry.get("player2"),
            "score": None,
            "sets_won": {},
            "status": entry.get("status"),
        }

    stats = None
    scoreboard_raw = None
    stats_error = None
    if fs_data and fs_data.get("id"):
        pause_between_sources()
        stats, scoreboard_raw, stats_error = _fetch_flashscore_enrichment(str(fs_data["id"]), locale)

    bf_match = betfair_match or {"player1": entry.get("player1"), "player2": entry.get("player2")}
    betfair_section = _build_betfair_section(event_data, bf_match)
    live_score = betfair_section.get("live_score")

    if fs_data and fs_data.get("id"):
        fresh = _fresh_flashscore_match(str(fs_data["id"]), sport=sport, locale=locale)
        if fresh:
            fs_data = fresh

    timestamp = _utc_now_iso()
    return {
        "timestamp": timestamp,
        "betfair_event_id": event_id_int,
        "flashscore_match_id": (fs_data or {}).get("id") or entry.get("flashscore_match_id"),
        "betfair": betfair_section,
        "flashscore": _build_flashscore_section(
            fs_data or {},
            stats,
            scoreboard_raw,
            live_score=live_score,
            stats_error=stats_error,
        ),
    }


def _load_flashscore_daily_index(*, sport: str, locale: str) -> dict[str, dict[str, Any]]:
    try:
        matches = filter_flashscore_matches(fs_get_matches(sport, locale=locale, live_only=False))
    except FlashscoreError:
        return {}
    return {str(match["id"]): match for match in matches if match.get("id")}


def _fetch_betfair_fixture(event_id: str | int) -> dict[str, Any] | None:
    try:
        client = BetfairClient()
        gql = GraphQLClient(client.app_key)
        eid = int(event_id)
        payload = gql.fetch_cards(
            [f"ppb:tbd:card:eventPrimaryMarket:{eid}"],
            view_urn=event_view_urn(eid),
            current_url=f"event/e-{eid}",
        )
        for card in iter_nodes_by_type(payload, "EventMarketCard"):
            fixture = card.get("fixture")
            if fixture:
                return fixture
    except (BetfairError, ValueError, OSError):
        return None
    return None


def _reconcile_tracked_match(
    entry: dict[str, Any],
    event_id: str,
    *,
    in_betfair_live: bool,
    in_flashscore_live: bool,
    fs_daily: dict[str, dict[str, Any]],
    now_iso: str,
) -> None:
    fs_id = str(entry.get("flashscore_match_id") or "")
    fs_match = fs_daily.get(fs_id) if fs_id else None

    betfair_fixture = None
    betfair_unreachable = False
    if not in_betfair_live:
        betfair_fixture = _fetch_betfair_fixture(event_id)
        betfair_unreachable = betfair_fixture is None

    if should_mark_finished(
        entry,
        in_betfair_live=in_betfair_live,
        in_flashscore_live=in_flashscore_live,
        fs_match=fs_match,
        betfair_fixture=betfair_fixture,
        betfair_unreachable=betfair_unreachable,
    ):
        apply_finished_state(entry, now_iso=now_iso, fs_match=fs_match, betfair_fixture=betfair_fixture)
        log.info("Partido finalizado event_id=%s (%s vs %s)", event_id, entry.get("player1"), entry.get("player2"))


def _update_entry_from_sources(
    entry: dict[str, Any],
    betfair_match: dict[str, Any] | None,
    fs_match: dict[str, Any] | None,
    *,
    now_iso: str,
) -> None:
    if entry_is_closed(entry):
        if fs_match and fs_match.get("score"):
            entry["score"] = fs_match["score"]
        if fs_match and fs_match.get("sets_won"):
            entry["sets_won"] = fs_match["sets_won"]
        entry["last_seen"] = now_iso
        return

    if betfair_match:
        entry["betfair_event_id"] = betfair_match.get("id", entry.get("betfair_event_id"))
        entry["player1"] = betfair_match.get("player1", entry.get("player1"))
        entry["player2"] = betfair_match.get("player2", entry.get("player2"))
        entry["competition"] = betfair_match.get("competition", entry.get("competition"))
        entry["status"] = betfair_match.get("status", entry.get("status"))
        entry["is_live"] = bool(betfair_match.get("is_live"))
        entry["betfair_url"] = betfair_match.get("url", entry.get("betfair_url"))
        if betfair_match.get("live_score"):
            entry["live_score"] = betfair_match["live_score"]
            merged_score = _score_label(entry)
            if merged_score:
                entry["score"] = merged_score

    if fs_match:
        entry["flashscore_match_id"] = fs_match.get("id", entry.get("flashscore_match_id"))
        entry["flashscore_url"] = fs_match.get("url", entry.get("flashscore_url"))
        if fs_match.get("score"):
            entry["score"] = fs_match["score"]
        if fs_match.get("sets_won"):
            entry["sets_won"] = fs_match["sets_won"]
        if fs_match.get("status"):
            entry["status"] = fs_match["status"]
        if "is_live" in fs_match:
            entry["is_live"] = bool(fs_match["is_live"])

    entry["last_seen"] = now_iso
    entry.setdefault("first_seen", now_iso)


def _should_drop_entry(entry: dict[str, Any], now: datetime) -> bool:
    finished_at = _parse_iso(entry.get("finished_at"))
    if not finished_at:
        return False
    if effective_is_live(entry):
        return False
    grace = timedelta(minutes=TRACK_GRACE_MINUTES)
    return now - finished_at > grace


def collect_once(
    *,
    sport: str = DEFAULT_SPORT,
    locale: str = DEFAULT_LOCALE,
    snapshot_callback: Callable[[str, dict[str, Any], dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Ejecuta un ciclo: descubre partidos en vivo y captura snapshots pendientes."""
    snapshots = 0
    errors = 0
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    pause_between_requests()
    try:
        betfair_live = filter_betfair_matches(get_live_matches(sport))
    except BetfairError as exc:
        log.error("Betfair: %s", exc)
        return {"snapshots": 0, "errors": 1, "message": str(exc)}

    pause_between_sources()
    try:
        flashscore_live = filter_flashscore_matches(fs_get_live_matches(sport, locale=locale))
    except FlashscoreError as exc:
        log.error("Flashscore: %s", exc)
        flashscore_live = []

    betfair_by_id = {str(m["id"]): m for m in betfair_live if m.get("id")}
    fs_by_id = {str(m["id"]): m for m in flashscore_live if m.get("id")}
    fs_daily = _load_flashscore_daily_index(sport=sport, locale=locale)

    index = load_index()
    matches = index.setdefault("matches", {})

    for event_id, bf_match in betfair_by_id.items():
        fs_match = find_flashscore_match(bf_match, flashscore_live)
        entry = matches.setdefault(event_id, {})
        is_new = entry.get("first_seen") is None
        _update_entry_from_sources(entry, bf_match, fs_match, now_iso=now_iso)
        if is_new:
            entry["queued_for_snapshot"] = True
        entry.pop("snapshot_error", None)

    for event_id, entry in list(matches.items()):
        in_betfair_live = event_id in betfair_by_id
        fs_id = str(entry.get("flashscore_match_id") or "")
        in_flashscore_live = fs_id in fs_by_id
        fs_daily_match = fs_daily.get(fs_id) if fs_id else None

        if in_betfair_live:
            bf_match = betfair_by_id[event_id]
            fs_match = fs_by_id.get(fs_id) or fs_daily_match
            _update_entry_from_sources(entry, bf_match, fs_match, now_iso=now_iso)
        else:
            _update_entry_from_sources(entry, None, fs_daily_match, now_iso=now_iso)

        _reconcile_tracked_match(
            entry,
            event_id,
            in_betfair_live=in_betfair_live,
            in_flashscore_live=in_flashscore_live,
            fs_daily=fs_daily,
            now_iso=now_iso,
        )

    for event_id in list(matches.keys()):
        if _should_drop_entry(matches[event_id], now):
            del matches[event_id]

    for event_id, entry in list(matches.items()):
        if not is_snapshot_due(entry, now):
            continue

        bf_match = betfair_by_id.get(event_id)
        fs_match = None
        fs_id = entry.get("flashscore_match_id")
        if fs_id:
            fs_match = fs_by_id.get(str(fs_id))
            if fs_match is None:
                fs_match = next(
                    (m for m in flashscore_live if str(m.get("id")) == str(fs_id)),
                    None,
                )

        try:
            snapshot = _capture_snapshot(
                event_id,
                entry,
                bf_match,
                fs_match,
                sport=sport,
                locale=locale,
            )
            save_snapshot(event_id, snapshot)
            schedule_next_snapshot(entry)
            entry.pop("snapshot_error", None)
            snapshots += 1
            log.info("Snapshot guardado event_id=%s", event_id)
            if snapshot_callback:
                try:
                    snapshot_callback(event_id, snapshot, dict(entry))
                except Exception:
                    log.exception("Error notificando snapshot al orquestador event_id=%s", event_id)
        except (BetfairError, FlashscoreError, OSError, ValueError) as exc:
            errors += 1
            entry["snapshot_error"] = str(exc)
            log.warning("Error snapshot event_id=%s: %s", event_id, exc)

        pause_between_requests()

    save_index(index)
    return {
        "snapshots": snapshots,
        "errors": errors,
        "matches_tracked": len(matches),
        "live_betfair": len(betfair_live),
        "live_flashscore": len(flashscore_live),
    }
