"""Captura de snapshots Betfair + Flashscore."""

from __future__ import annotations

import logging
import shutil
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from collector.paths import DATA_DIR, ensure_scraper_paths

ensure_scraper_paths()

from collector.anti_block import pause_between_requests, pause_between_sources
from collector.config import (
    DEFAULT_LOCALE,
    DEFAULT_SPORT,
    PURGE_ORPHAN_MATCH_DIRS,
    STALE_SNAPSHOT_HOURS,
    TRACK_GRACE_MINUTES,
    UNREACHABLE_STALE_MINUTES,
)
from collector.filters import filter_betfair_matches, filter_flashscore_matches
from collector.matcher import find_flashscore_match
from collector.match_status import (
    apply_finished_state,
    entry_is_closed,
    should_mark_finished,
    status_is_finished,
)

from collector.score_merge import (
    build_flashscore_section,
    parse_sets_detail as _parse_sets_detail,
    score_label as _score_label,
)
from collector.storage import (
    _parse_iso,
    _utc_now_iso,
    effective_is_live,
    is_snapshot_due,
    load_index,
    load_meta,
    save_index,
    save_snapshot,
    schedule_next_snapshot,
)

ensure_scraper_paths()
from betfair_scraper.client import BetfairClient, BetfairError
from betfair_scraper.graphql import GraphQLClient, event_view_urn
from betfair_scraper.parser import iter_nodes_by_type
from betfair_scraper.scraper import get_event_markets, get_live_matches
from flashscore_scraper import get_live_matches as fs_get_live_matches
from flashscore_scraper import get_match_statistics, get_matches as fs_get_matches
from flashscore_scraper.client import FlashscoreClient, FlashscoreError
from flashscore_scraper.parser import parse_scoreboard_feed

log = logging.getLogger("collector.snapshot")


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
    scoreboard_error: str | None = None,
) -> dict[str, Any]:
    player1 = fs_match.get("player1", "")
    player2 = fs_match.get("player2", "")
    return build_flashscore_section(
        fs_match,
        stats,
        scoreboard_raw,
        live_score=live_score,
        stats_error=stats_error,
        scoreboard_error=scoreboard_error,
        winner_side=_side_from_winner(fs_match.get("winner"), player1, player2),
    )


def _fetch_flashscore_enrichment(
    match_id: str,
    locale: str,
) -> tuple[
    dict[str, Any] | None,
    dict[str, str] | None,
    str | None,
    str | None,
]:
    stats: dict[str, Any] | None = None
    scoreboard_raw: dict[str, str] | None = None
    stats_error: str | None = None
    scoreboard_error: str | None = None

    try:
        stats = get_match_statistics(match_id, locale=locale)
    except FlashscoreError as exc:
        stats_error = str(exc)

    try:
        client = FlashscoreClient(locale=locale)
        raw = client.get_match_scoreboard(match_id)
        scoreboard_raw = parse_scoreboard_feed(raw)
    except FlashscoreError as exc:
        scoreboard_error = str(exc)

    return stats, scoreboard_raw, stats_error, scoreboard_error


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
    scoreboard_error = None
    if fs_data and fs_data.get("id"):
        pause_between_sources()
        stats, scoreboard_raw, stats_error, scoreboard_error = (
            _fetch_flashscore_enrichment(str(fs_data["id"]), locale)
        )

    bf_match = betfair_match or {"player1": entry.get("player1"), "player2": entry.get("player2")}
    betfair_section = _build_betfair_section(event_data, bf_match)
    live_score = betfair_section.get("live_score")

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
            scoreboard_error=scoreboard_error,
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
    now = _parse_iso(now_iso)

    if (
        not in_betfair_live
        and not in_flashscore_live
        and not entry_is_closed(entry)
        and now is not None
    ):
        last_snap = _parse_iso(entry.get("last_snapshot_at"))
        if last_snap and now - last_snap > timedelta(hours=STALE_SNAPSHOT_HOURS):
            entry["is_live"] = False
            entry["is_stale"] = True
            entry.setdefault("stale_at", now_iso)
            entry["status"] = entry.get("status") or "No disponible"
            entry.pop("next_snapshot_at", None)
            entry.pop("queued_for_snapshot", None)
            log.warning(
                "Partido histórico fuera de feeds live event_id=%s (%s vs %s)",
                event_id,
                entry.get("player1"),
                entry.get("player2"),
            )
            return

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
        return

    last_source_seen = _parse_iso(
        entry.get("last_source_seen_at")
        or entry.get("last_snapshot_at")
        or entry.get("first_seen")
    )
    now = _parse_iso(now_iso)
    if (
        betfair_unreachable
        and not in_betfair_live
        and not in_flashscore_live
        and fs_match is None
        and last_source_seen is not None
        and now is not None
        and now - last_source_seen
        > timedelta(minutes=UNREACHABLE_STALE_MINUTES)
    ):
        entry["is_live"] = False
        entry["is_stale"] = True
        entry.setdefault("stale_at", now_iso)
        entry["status"] = "No disponible"
        entry.pop("next_snapshot_at", None)
        entry.pop("queued_for_snapshot", None)
        log.warning("Partido obsoleto eliminado de captura event_id=%s", event_id)


def _update_entry_from_sources(
    entry: dict[str, Any],
    betfair_match: dict[str, Any] | None,
    fs_match: dict[str, Any] | None,
    *,
    now_iso: str,
    revive_from_source: bool = True,
) -> None:
    if entry_is_closed(entry):
        if fs_match and fs_match.get("score"):
            entry["score"] = fs_match["score"]
        if fs_match and fs_match.get("sets_won"):
            entry["sets_won"] = fs_match["sets_won"]
        entry["last_seen"] = now_iso
        return

    if revive_from_source and (betfair_match or fs_match):
        entry["last_source_seen_at"] = now_iso
        entry.pop("is_stale", None)
        entry.pop("stale_at", None)

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
        if fs_match.get("start_time"):
            entry["match_start_time"] = fs_match.get("start_time")
        if fs_match.get("start_timestamp"):
            entry["match_start_timestamp"] = fs_match.get("start_timestamp")
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
    if effective_is_live(entry):
        return False

    stale_at = _parse_iso(entry.get("stale_at"))
    if entry.get("is_stale") and stale_at:
        last_snap = _parse_iso(entry.get("last_snapshot_at"))
        historical = (
            last_snap is None
            or now - last_snap > timedelta(hours=STALE_SNAPSHOT_HOURS)
        )
        grace = timedelta(minutes=2 if historical else TRACK_GRACE_MINUTES)
        if now - stale_at > grace:
            return True

    finished_at = _parse_iso(entry.get("finished_at"))
    if finished_at:
        return now - finished_at > timedelta(minutes=TRACK_GRACE_MINUTES)

    return False


def _match_dir_has_training_artifacts(directory) -> bool:
    """True si el dir guarda trayectoria/informes útiles para SFT o auditoría."""
    if (directory / "generalist_turns.jsonl").exists():
        return True
    reports = directory / "reports"
    if reports.is_dir() and any(reports.iterdir()):
        return True
    records = directory / "analysis_records"
    if records.is_dir() and any(records.iterdir()):
        return True
    if (directory / "decision.md").exists() or (directory / "context.md").exists():
        return True
    return False


def _purge_orphan_match_directories(
    active_event_ids: set[str],
    now: datetime,
) -> int:
    """
    Elimina directorios de partido fuera del índice activo.

    Desactivado por defecto (PURGE_ORPHAN_MATCH_DIRS=false): el dataset de
    training vive en esos directorios tras salir del índice live. Aunque el
    flag esté on, nunca borra dirs con turns/reports/analysis_records.
    """
    if not PURGE_ORPHAN_MATCH_DIRS:
        return 0
    if not DATA_DIR.exists():
        return 0
    purged = 0
    skipped_training = 0
    grace = timedelta(hours=STALE_SNAPSHOT_HOURS)
    for directory in DATA_DIR.iterdir():
        if not directory.is_dir() or not directory.name.isdigit():
            continue
        event_id = directory.name
        if event_id in active_event_ids:
            continue
        if _match_dir_has_training_artifacts(directory):
            skipped_training += 1
            continue
        meta = load_meta(event_id)
        last_at = _parse_iso(meta.get("last_snapshot_at"))
        if last_at and now - last_at < grace:
            continue
        try:
            shutil.rmtree(directory)
            purged += 1
            log.info("Directorio huérfano purgado event_id=%s", event_id)
        except OSError as exc:
            log.warning("No se pudo purgar directorio huérfano %s: %s", event_id, exc)
    if skipped_training:
        log.info(
            "Purga huérfanos: %s dir(s) conservados por artefactos de training",
            skipped_training,
        )
    return purged


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
            # El calendario diario de Flashscore no debe revivir partidos fuera de Betfair live.
            entry["last_seen"] = now_iso

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

    orphans_purged = _purge_orphan_match_directories(set(matches.keys()), now)
    save_index(index)
    return {
        "snapshots": snapshots,
        "errors": errors,
        "matches_tracked": len(matches),
        "live_betfair": len(betfair_live),
        "live_flashscore": len(flashscore_live),
        "orphans_purged": orphans_purged,
    }
