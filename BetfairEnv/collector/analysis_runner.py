"""Orquestación automática de analistas y generalista por partido."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from collector.paths import DATA_DIR, ROOT
from collector.shutdown_utils import void_open_positions_on_shutdown
from collector.storage import (
    _atomic_write_text,
    effective_is_live,
    list_snapshot_files,
    load_index,
    load_meta,
    load_snapshot,
    match_dir,
    prune_match_snapshots,
    save_index,
    save_meta,
)
from tennisAgents.default_config import DEFAULT_CONFIG
from tennisAgents.agents.generalist import (
    _bet_calibration_fields,
    _market_family,
    _save_turn_log,
    _write_context_file,
    format_decision_display,
)
from tennisAgents.agents.utils.report_utils import sanitize_analyst_report
from tennisAgents.dataflows.market_resolve import (
    build_game_winners_from_scores,
    derive_sets_won,
    normalize_text,
    parse_sets_detail,
    resolve_market_selection,
    set_is_complete,
)
from tennisAgents.dataflows.tournament_utils import normalize_tournament, resolve_tournament_identity
from collector.match_status import (
    has_decisive_match_winner,
    match_decided_by_sets,
    winner_side,
)
from tennisAgents.graph.trading_graph import TennisAgentsGraph
from tennisAgents.utils.enumerations import REPORTS, STATE

log = logging.getLogger("collector.analysis")

REPORT_KEYS = (
    REPORTS.news_report,
    REPORTS.players_report,
    REPORTS.tournament_report,
    REPORTS.weather_report,
)
COLLECTOR_META_KEYS = (
    "betfair_event_id",
    "flashscore_match_id",
    "last_snapshot_at",
    "snapshots_count",
    "snapshot_retention_blocked",
)


class AnalysisDeferredError(RuntimeError):
    """Error recuperable: el snapshot debe permanecer pendiente."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _market_selection(
    snapshot: dict[str, Any],
    market_type: str,
    option: str,
    *,
    market_id: str | None = None,
    selection_id: Any = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    betfair = snapshot.get("betfair") or {}
    return resolve_market_selection(
        list(betfair.get("markets") or []),
        market_type,
        option,
        market_id=market_id,
        selection_id=selection_id,
        primary_market=betfair.get("primary_market") or {},
    )


def _snapshot_tradeable(snapshot: dict[str, Any]) -> tuple[bool, str]:
    """Evita Bet solo cuando falta el enlace Flashscore o no hay mercados abiertos."""
    flashscore = snapshot.get("flashscore") or {}
    flashscore_match = flashscore.get("match") or {}
    flashscore_id = snapshot.get("flashscore_match_id") or flashscore_match.get("id")
    if not flashscore_id:
        return False, "Snapshot sin enlace confirmado con Flashscore."

    betfair = snapshot.get("betfair") or {}
    markets = list(betfair.get("markets") or [])
    primary = betfair.get("primary_market") or {}
    if primary:
        markets = [primary, *markets]
    open_markets = [
        market
        for market in markets
        if str(market.get("status") or "").upper() in {"", "OPEN"}
    ]
    if not open_markets:
        return False, "Snapshot sin mercados abiertos para apostar."
    # Un marcador Flashscore 0-0 con mercados de set 2/3 suele ser lag del feed,
    # no una incoherencia bloqueante: el matching y la cuota real siguen mandando.
    return True, ""


def _policy_wait(record: dict[str, Any], reason: str, original: dict[str, Any]) -> dict[str, Any]:
    safe_record = deepcopy(record)
    safe_record["target"]["tool_call"] = {
        "name": "wait",
        "technical_fallback": False,
        "policy_rejected": True,
        "original_tool_call": original,
        "arguments": {
            "reason": f"Acción rechazada por política de seguridad: {reason}",
            "confidence": 1.0,
            "next_trigger": "Esperar un snapshot coherente y una acción válida.",
            "notes": "No se modificaron saldo ni posiciones.",
        },
    }
    outcome = safe_record.setdefault("outcome", {})
    outcome["accepted_for_training"] = False
    outcome["label_source"] = "safety_policy"
    return safe_record


def _yes_no_expectation(selection: str) -> bool | None:
    tokens = normalize_text(selection).split()
    if not tokens:
        return None
    answer = tokens[-1]
    if answer in {"si", "yes", "true"}:
        return True
    if answer in {"no", "false"}:
        return False
    if normalize_text(selection) in {"si", "yes"}:
        return True
    if normalize_text(selection) in {"no"}:
        return False
    return None


def _player_side(
    selection: str,
    player1: str,
    player2: str,
) -> str | None:
    wanted = normalize_text(selection)
    p1 = normalize_text(player1)
    p2 = normalize_text(player2)
    if not wanted:
        return None
    if p1 and (wanted == p1 or wanted.startswith(p1 + " ") or p1 in wanted):
        if p2 and p2 in wanted and len(p2) > len(p1):
            return "player2"
        return "player1"
    if p2 and (wanted == p2 or wanted.startswith(p2 + " ") or p2 in wanted):
        return "player2"
    return None


def _enrich_entry_from_scores(
    entry: dict[str, Any],
    scores: list[str],
) -> dict[str, Any]:
    enriched = dict(entry)
    if scores:
        detail = parse_sets_detail(scores[-1])
        if detail:
            enriched["sets_detail"] = detail
            derived = derive_sets_won(detail)
            if derived["player1"] or derived["player2"]:
                enriched["sets_won"] = derived
    elif entry.get("score"):
        detail = parse_sets_detail(str(entry.get("score")))
        if detail:
            enriched.setdefault("sets_detail", detail)
            derived = derive_sets_won(detail)
            if derived["player1"] or derived["player2"]:
                enriched.setdefault("sets_won", derived)
    return enriched


def _settlement_result(
    position: dict[str, Any],
    entry: dict[str, Any],
    *,
    game_winners: dict[tuple[int, int], str] | None = None,
) -> bool | None:
    """Liquida mercados demostrables con resultado final o progresión de juegos."""
    winner_side = str(entry.get("winner") or "")
    player1 = str(entry.get("player1") or "").strip()
    player2 = str(entry.get("player2") or "").strip()
    selection = str(position.get("selection") or "").strip()
    market = str(position.get("market") or "").upper()
    sets_detail = list(entry.get("sets_detail") or parse_sets_detail(entry.get("score")))
    sets_won = entry.get("sets_won") or derive_sets_won(sets_detail)
    p1_sets = int(_safe_float(sets_won.get("player1"), 0.0))
    p2_sets = int(_safe_float(sets_won.get("player2"), 0.0))

    if market == "MATCH_ODDS":
        if winner_side not in {"player1", "player2"}:
            return None
        selected_side = _player_side(selection, player1, player2)
        return selected_side == winner_side if selected_side else None

    expected_yes = _yes_no_expectation(selection)
    if market == "PLAYER_A_TO_WIN_AT_LEAST_1_SET":
        if expected_yes is None:
            return None
        return (p1_sets >= 1) == expected_yes
    if market == "PLAYER_B_TO_WIN_AT_LEAST_1_SET":
        if expected_yes is None:
            return None
        return (p2_sets >= 1) == expected_yes
    if market in {"BOTH_PLAYERS_TO_WIN_A_SET_YES/NO", "BOTH_PLAYERS_TO_WIN_A_SET"}:
        if expected_yes is None:
            return None
        both = p1_sets >= 1 and p2_sets >= 1
        # Si el partido ya terminó sin que ambos ganaran un set, el No es resoluble.
        if both:
            return expected_yes is True
        if winner_side in {"player1", "player2"}:
            return expected_yes is False
        return None

    if market in {"SET_BETTING", "SET_BETTING_STANDARD"}:
        score_match = re.search(r"([0-3])-([0-3])$", normalize_text(selection))
        if not score_match:
            return None
        expected = (int(score_match.group(1)), int(score_match.group(2)))
        selected_side = _player_side(selection, player1, player2)
        if selected_side == "player1":
            actual = (p1_sets, p2_sets)
        elif selected_side == "player2":
            actual = (p2_sets, p1_sets)
        else:
            return None
        if winner_side not in {"player1", "player2"}:
            return None
        return actual == expected

    set_winner = re.fullmatch(r"SET_0?([1-3])_WINNER", market)
    if set_winner:
        set_idx = int(set_winner.group(1)) - 1
        if set_idx >= len(sets_detail):
            return None
        games = sets_detail[set_idx]
        a = int(games.get("player1") or 0)
        b = int(games.get("player2") or 0)
        if not set_is_complete(a, b):
            return None
        set_side = "player1" if a > b else "player2"
        selected_side = _player_side(selection, player1, player2)
        return selected_side == set_side if selected_side else None

    correct = re.fullmatch(r"CORRECT_SCORE_(1ST|2ND|3RD)_SET", market)
    if correct:
        ordinal = {"1ST": 0, "2ND": 1, "3RD": 2}[correct.group(1)]
        if ordinal >= len(sets_detail):
            return None
        games = sets_detail[ordinal]
        a = int(games.get("player1") or 0)
        b = int(games.get("player2") or 0)
        if not set_is_complete(a, b):
            return None
        score_match = re.search(r"(\d+)\s*-\s*(\d+)$", selection)
        if not score_match:
            return None
        expected = (int(score_match.group(1)), int(score_match.group(2)))
        selected_side = _player_side(selection, player1, player2)
        if selected_side == "player1":
            actual = (a, b)
        elif selected_side == "player2":
            actual = (b, a)
        else:
            return None
        return actual == expected

    total = re.fullmatch(
        r"SET_([1-3])_TOTAL_GAMES_OVER/UNDER_(\d+(?:\.\d+)?)",
        market,
    )
    if total:
        set_idx = int(total.group(1)) - 1
        line = float(total.group(2))
        if set_idx >= len(sets_detail):
            return None
        games = sets_detail[set_idx]
        a = int(games.get("player1") or 0)
        b = int(games.get("player2") or 0)
        if not set_is_complete(a, b):
            return None
        total_games = a + b
        went_over = total_games > line
        option = normalize_text(selection)
        if "mas" in option or "over" in option:
            return went_over
        if "menos" in option or "under" in option:
            return not went_over
        return None

    game_market = re.fullmatch(r"SET_([1-3])_GAME_(\d+)_WINNER", market)
    if game_market:
        key = (int(game_market.group(1)), int(game_market.group(2)))
        side = (game_winners or {}).get(key)
        if side not in {"player1", "player2"}:
            return None
        selected_side = _player_side(selection, player1, player2)
        return selected_side == side if selected_side else None

    return None


def _apply_settled_position(
    *,
    position: dict[str, Any],
    won: bool,
    available_balance: float,
    realized_pnl: float,
    history: list[dict[str, Any]],
    event_name: str = "settled",
) -> tuple[float, float]:
    stake = _safe_float(
        position.get("remaining_stake", position.get("initial_stake")),
        0.0,
    )
    odds = _safe_float(position.get("entry_odds"), 0.0)
    pnl = stake * (odds - 1.0) if won else -stake
    payout = stake * odds if won else 0.0
    available_balance += payout
    realized_pnl += pnl
    history.append(
        {
            "event": event_name,
            "position_id": position.get("position_id"),
            "settled_at": _utc_now_iso(),
            "won": won,
            "stake": stake,
            "odds": odds,
            "pnl": pnl,
        }
    )
    return available_balance, realized_pnl


def _void_position(
    *,
    position: dict[str, Any],
    available_balance: float,
    history: list[dict[str, Any]],
    reason: str,
) -> float:
    stake = _safe_float(
        position.get("remaining_stake", position.get("initial_stake")),
        0.0,
    )
    available_balance += stake
    history.append(
        {
            "event": "voided",
            "position_id": position.get("position_id"),
            "voided_at": _utc_now_iso(),
            "stake": stake,
            "pnl": 0.0,
            "reason": reason,
        }
    )
    return available_balance


class AutomatedAnalysisRunner:
    """
    Ejecuta el análisis automático asociado a los snapshots del colector.

    Los analistas se ejecutan una sola vez por event_id. El generalista se
    ejecuta una vez por cada snapshot y conserva su contexto en context.md.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Solo se mantiene en memoria la señal de que un partido necesita
        # trabajo. Los snapshots completos permanecen en disco, de modo que
        # una cola larga no consume memoria durante ejecuciones prolongadas.
        self._pending: dict[str, dict[str, Any]] = {}
        self._processing: set[str] = set()
        self._retry_timers: dict[str, threading.Timer] = {}
        self._graph_local = threading.local()
        self._shutting_down = False
        self._provider_circuit_until: datetime | None = None
        self._event_locks_guard = threading.Lock()
        self._event_locks: dict[str, threading.RLock] = {}

        self.config = DEFAULT_CONFIG.copy()
        self.config.update(
            {
                "project_dir": str(ROOT.parent),
                "results_dir": str(ROOT / "data"),
                "tool_outputs_log": str(ROOT / "data" / "automated_tool_outputs.jsonl"),
                "progress_callback": None,
            }
        )
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, int(self.config.get("automated_analysis_workers", 2))),
            thread_name_prefix="tennis-analysis",
        )
        log.info(
            "LLM automático: provider=%s model=%s backend=%s",
            self.config.get("llm_provider"),
            self.config.get("deep_think_llm"),
            self.config.get("backend_url"),
        )

    def _get_graph(self) -> TennisAgentsGraph:
        graph = getattr(self._graph_local, "graph", None)
        if graph is None:
            graph = TennisAgentsGraph(
                selected_analysts=["news", "players", "tournament", "weather"],
                config=self.config,
                debug=False,
            )
            self._graph_local.graph = graph
        return graph

    def _event_lock(self, event_id: str) -> threading.RLock:
        event_key = str(event_id)
        with self._event_locks_guard:
            return self._event_locks.setdefault(event_key, threading.RLock())

    def _save_analysis_meta(
        self,
        event_id: str,
        meta: dict[str, Any],
        *,
        remove_keys: tuple[str, ...] = (),
    ) -> None:
        save_meta(
            event_id,
            meta,
            remove_keys=remove_keys,
            preserve_existing_keys=COLLECTOR_META_KEYS,
        )

    def submit_snapshot(
        self,
        event_id: str,
        snapshot: dict[str, Any],
        entry: dict[str, Any],
    ) -> None:
        """Señala que hay snapshots pendientes para este partido."""
        event_key = str(event_id)
        with self._lock:
            if self._shutting_down:
                raise RuntimeError("El orquestador de análisis se está deteniendo.")
            self._pending[event_key] = dict(entry)
            if event_key in self._processing:
                return
            self._processing.add(event_key)
        self._executor.submit(self._drain_event, event_key)

    def shutdown(self) -> None:
        """Completa la tarea activa, liquida lo posible y evita perder estado."""
        with self._lock:
            self._shutting_down = True
            for timer in self._retry_timers.values():
                timer.cancel()
            self._retry_timers.clear()
        self._executor.shutdown(wait=True, cancel_futures=True)
        drain_sec = max(
            0,
            int(self.config.get("shutdown_drain_sec", 5) or 0),
        )
        if drain_sec > 0:
            deadline = time.monotonic() + drain_sec
            while time.monotonic() < deadline:
                with self._lock:
                    busy = bool(self._processing)
                if not busy:
                    break
                time.sleep(0.2)
        try:
            reconciled = self.reconcile_finished_matches()
            if reconciled:
                log.info(
                    "Drain de shutdown: partidos reconciliados=%s",
                    reconciled,
                )
        except Exception:
            log.exception("Drain de shutdown: fallo reconciliando partidos")
        try:
            settled = self._close_or_settle_open_positions_on_shutdown()
            if settled:
                log.info(
                    "Drain de shutdown: posiciones liquidadas/cerradas=%s",
                    settled,
                )
        except Exception:
            log.exception("Drain de shutdown: fallo liquidando posiciones")
        self._void_open_positions_on_shutdown()

    def _void_open_positions_on_shutdown(self) -> None:
        """Devuelve stakes de posiciones abiertas al apagar el colector."""
        void_open_positions_on_shutdown(self.config)

    def _latest_snapshot(self, event_id: str) -> dict[str, Any] | None:
        items = list_snapshot_files(event_id)
        if not items:
            return None
        try:
            return load_snapshot(event_id, items[-1]["file"])
        except (OSError, json.JSONDecodeError, KeyError):
            return None

    def _close_or_settle_open_positions_on_shutdown(self) -> int:
        """
        Intenta Close (cash-out) o settlement por marcador antes del void.

        Devuelve el número de posiciones resueltas. Las que fallen quedan
        para void_open_positions_on_shutdown.
        """
        if not self.config.get("settle_open_positions_on_shutdown", True):
            return 0
        if not DATA_DIR.exists():
            return 0

        resolved = 0
        for directory in DATA_DIR.iterdir():
            if not directory.is_dir() or not directory.name.isdigit():
                continue
            event_id = directory.name
            with self._event_lock(event_id):
                meta = load_meta(event_id)
                open_positions = [
                    position
                    for position in (meta.get("open_positions") or [])
                    if isinstance(position, dict)
                ]
                if not open_positions:
                    continue
                snapshot = self._latest_snapshot(event_id) or {
                    "betfair": {},
                    "flashscore": {},
                }
                history = list(meta.get("position_history") or [])
                available_balance = _safe_float(
                    meta.get(
                        "available_balance",
                        meta.get(
                            "wallet_balance",
                            self.config.get("automated_wallet_balance", 100.0),
                        ),
                    ),
                    100.0,
                )
                realized_pnl = _safe_float(meta.get("realized_pnl"), 0.0)
                remaining: list[dict[str, Any]] = []
                scores = self._event_score_history(event_id)
                flash_score = str(
                    (snapshot.get("flashscore") or {}).get("score") or ""
                ).strip()
                if flash_score and (not scores or scores[-1] != flash_score):
                    scores = [*scores, flash_score]
                game_winners = build_game_winners_from_scores(scores)
                settle_entry = _enrich_entry_from_scores(
                    {
                        "player1": meta.get("analysis_player1")
                        or (snapshot.get("betfair") or {}).get("player1"),
                        "player2": meta.get("analysis_player2")
                        or (snapshot.get("betfair") or {}).get("player2"),
                        "score": flash_score or (scores[-1] if scores else None),
                        "winner": (snapshot.get("flashscore") or {}).get("winner"),
                        "sets_won": (snapshot.get("flashscore") or {}).get("sets_won"),
                    },
                    scores,
                )

                for position in open_positions:
                    market, runner = _market_selection(
                        snapshot,
                        str(position.get("market") or ""),
                        str(position.get("selection") or ""),
                        market_id=str(position.get("market_id") or "") or None,
                        selection_id=position.get("selection_id"),
                    )
                    stake = _safe_float(
                        position.get(
                            "remaining_stake",
                            position.get("initial_stake"),
                        ),
                        0.0,
                    )
                    entry_odds = _safe_float(position.get("entry_odds"), 0.0)
                    closed_at = _utc_now_iso()

                    if (
                        market
                        and runner
                        and str(market.get("status") or "").upper() in {"", "OPEN"}
                        and str(runner.get("status") or "").upper()
                        in {"", "ACTIVE"}
                    ):
                        exit_odds = _safe_float(runner.get("odds_decimal"), 0.0)
                        if exit_odds > 1.0 and entry_odds > 0:
                            pnl = stake * ((entry_odds / exit_odds) - 1.0)
                            available_balance += stake + pnl
                            realized_pnl += pnl
                            history.append(
                                {
                                    "event": "closed_on_shutdown",
                                    "position_id": position.get("position_id"),
                                    "closed_at": closed_at,
                                    "closed_stake": stake,
                                    "entry_odds": entry_odds,
                                    "exit_odds": exit_odds,
                                    "realized_pnl": pnl,
                                    "reason": (
                                        "Cash-out simulado al apagar el colector."
                                    ),
                                }
                            )
                            resolved += 1
                            continue

                    won = _settlement_result(
                        position,
                        settle_entry,
                        game_winners=game_winners,
                    )
                    if won is None:
                        remaining.append(position)
                        continue
                    available_balance, realized_pnl = _apply_settled_position(
                        position=position,
                        won=won,
                        available_balance=available_balance,
                        realized_pnl=realized_pnl,
                        history=history,
                        event_name="settled_on_shutdown",
                    )
                    history[-1]["reason"] = (
                        "Liquidación por marcador al apagar el colector."
                    )
                    resolved += 1

                meta["open_positions"] = remaining
                meta["position_history"] = history
                meta["available_balance"] = round(available_balance, 8)
                meta["realized_pnl"] = round(realized_pnl, 8)
                if resolved and not remaining:
                    meta["settlement_status"] = "settled_on_shutdown"
                    if meta.get("analysis_status") not in {
                        "finished",
                        "finished_unsettled",
                    }:
                        meta["analysis_status"] = "stopped_settled"
                self._save_analysis_meta(event_id, meta)
        return resolved

    def reconcile_session_on_startup(self) -> dict[str, int]:
        """
        Autocuración al reanudar tras paradas largas o bruscas.

        Objetivo: que un defecto puntual (estado a medias, superficie vieja,
        posiciones abiertas en partidos cerrados) no se propague al siguiente ciclo.
        """
        stats = {
            "stuck_status_reset": 0,
            "analysts_invalidated": 0,
            "positions_voided": 0,
            "index_synced": 0,
            "events_healed": 0,
        }
        index = load_index()
        matches = index.setdefault("matches", {})
        index_dirty = False

        for event_id, entry in list(matches.items()):
            meta = load_meta(event_id)
            last_at = meta.get("last_snapshot_at")
            if last_at and entry.get("last_snapshot_at") != last_at:
                entry["last_snapshot_at"] = last_at
                index_dirty = True
                stats["index_synced"] += 1
        if index_dirty:
            save_index(index)

        if not DATA_DIR.exists():
            return stats

        for directory in DATA_DIR.iterdir():
            if not directory.is_dir() or not directory.name.isdigit():
                continue
            event_id = directory.name
            with self._event_lock(event_id):
                meta = load_meta(event_id)
                if not meta:
                    continue
                entry = dict(matches.get(event_id) or {})
                changed = False

                if meta.get("analysis_status") in {"analysts_running", "generalist_running"}:
                    meta["analysis_status"] = "running"
                    meta.pop("analysis_current_snapshot_at", None)
                    meta.pop("analysis_current_started_at", None)
                    changed = True
                    stats["stuck_status_reset"] += 1

                if (
                    meta.get("analysis_status") == "stopped_unsettled"
                    and entry
                    and effective_is_live(entry)
                ):
                    meta["analysis_status"] = "running"
                    changed = True

                if (
                    not meta.get("analysts_completed")
                    and meta.get("analysis_status") == "error"
                ):
                    meta["analysis_status"] = "running"
                    meta.pop("analysis_error", None)
                    changed = True

                open_positions = [
                    position
                    for position in (meta.get("open_positions") or [])
                    if isinstance(position, dict)
                ]
                if open_positions and self._should_void_positions_on_resume(entry, meta):
                    history = list(meta.get("position_history") or [])
                    available_balance = _safe_float(
                        meta.get(
                            "available_balance",
                            meta.get(
                                "wallet_balance",
                                self.config.get("automated_wallet_balance", 100.0),
                            ),
                        ),
                        100.0,
                    )
                    for position in open_positions:
                        available_balance = _void_position(
                            position=position,
                            available_balance=available_balance,
                            history=history,
                            reason=(
                                "Posición abierta al reanudar sesión; "
                                "stake devuelto (void) por autocuración de arranque."
                            ),
                        )
                        stats["positions_voided"] += 1
                    meta["open_positions"] = []
                    meta["position_history"] = history
                    meta["available_balance"] = round(available_balance, 8)
                    if not str(meta.get("analysis_status") or "").startswith("finished"):
                        meta["settlement_status"] = "voided_on_resume"
                    changed = True

                snapshots = list_snapshot_files(event_id)
                if snapshots:
                    try:
                        snapshot = load_snapshot(event_id, snapshots[-1]["file"])
                    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                        snapshot = None
                    if snapshot:
                        identity = self._resolve_tournament_identity(
                            snapshot,
                            entry,
                            meta,
                        )
                        drift = self._tournament_identity_drift(meta, identity)
                        sync_changed = self._sync_analysis_tournament(meta, identity)
                        if sync_changed:
                            changed = True
                        if meta.get("analysts_completed") and (drift or sync_changed):
                            meta["analysts_completed"] = False
                            meta.pop("analyst_report_errors", None)
                            changed = True
                            stats["analysts_invalidated"] += 1
                        reports = self._load_reports(event_id)
                        report_errors = self._report_quality_errors(reports)
                        if meta.get("analysts_completed") and report_errors:
                            meta["analysts_completed"] = False
                            meta["analyst_report_errors"] = report_errors
                            changed = True
                            stats["analysts_invalidated"] += 1

                if changed:
                    self._save_analysis_meta(event_id, meta)
                    stats["events_healed"] += 1

        return stats

    @staticmethod
    def _entry_is_finished(entry: dict[str, Any], meta: dict[str, Any]) -> bool:
        status = str(entry.get("status") or "").lower()
        if entry.get("is_finished") or entry.get("finished_at"):
            return True
        if str(meta.get("analysis_status") or "").startswith("finished"):
            return True
        return any(
            token in status
            for token in ("final", "terminad", "finished", "retirad", "walkover")
        )

    def _should_void_positions_on_resume(
        self,
        entry: dict[str, Any],
        meta: dict[str, Any],
    ) -> bool:
        if meta.get("settlement_status") == "voided_on_shutdown":
            return True
        if self._entry_is_finished(entry, meta):
            return True
        if entry and not effective_is_live(entry):
            return True
        if not entry and str(meta.get("analysis_status") or "").startswith("finished"):
            return True
        return False

    def resume_pending(self) -> int:
        """Reanuda snapshots no procesados después de un reinicio."""
        index_matches = (load_index().get("matches") or {})
        resumed = 0
        if not DATA_DIR.exists():
            return resumed
        for directory in DATA_DIR.iterdir():
            if not directory.is_dir() or not directory.name.isdigit():
                continue
            event_id = directory.name
            meta = load_meta(event_id)
            last_processed = str(meta.get("last_processed_snapshot_at") or "")
            snapshots = list_snapshot_files(event_id)
            if not snapshots or str(snapshots[-1].get("timestamp") or "") <= last_processed:
                continue
            entry = dict(index_matches.get(event_id) or {})
            if not entry:
                latest = load_snapshot(event_id, snapshots[-1]["file"])
                betfair = latest.get("betfair") or {}
                entry = {
                    "betfair_event_id": latest.get("betfair_event_id"),
                    "player1": betfair.get("player1"),
                    "player2": betfair.get("player2"),
                    "competition": betfair.get("competition"),
                    "is_live": bool(betfair.get("is_live")),
                }
            self.submit_snapshot(event_id, {}, entry)
            resumed += 1
        return resumed

    def sanitize_training_labels(self) -> int:
        """Pone en cuarentena turnos legacy sin resultado o procedencia válida."""
        changed_records = 0
        if not DATA_DIR.exists():
            return changed_records
        for directory in DATA_DIR.iterdir():
            if not directory.is_dir():
                continue
            turns_path = directory / "generalist_turns.jsonl"
            if not turns_path.exists():
                continue
            updated_lines: list[str] = []
            file_changed = False
            for line in turns_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                turn = json.loads(line)
                target = (turn.get("target") or {}).get("tool_call") or {}
                arguments = target.get("arguments") or {}
                reason = str(arguments.get("reason") or "").casefold()
                legacy_fallback = bool(
                    target.get("name") == "wait"
                    and _safe_float(arguments.get("confidence"), -1.0) == 0.0
                    and "tool call válida" in reason
                )
                if legacy_fallback and not target.get("technical_fallback"):
                    target["technical_fallback"] = True
                    file_changed = True
                outcome = turn.setdefault("outcome", {})
                eligible = bool(
                    outcome.get("eventual_match_winner") is not None
                    and outcome.get("pnl_after_match") is not None
                    and not target.get("technical_fallback")
                    and not target.get("policy_rejected")
                )
                if outcome.get("accepted_for_training") != eligible:
                    outcome["accepted_for_training"] = eligible
                    outcome["label_source"] = (
                        "settled_match" if eligible else "legacy_unsettled"
                    )
                    file_changed = True
                    changed_records += 1
                updated_lines.append(json.dumps(turn, ensure_ascii=False))
            if file_changed:
                _atomic_write_text(
                    turns_path,
                    "\n".join(updated_lines) + ("\n" if updated_lines else ""),
                )
        return changed_records

    def migrate_legacy_ledgers(self) -> int:
        """Aísla saldos/posiciones creados antes del ledger reconciliable."""
        migrated = 0
        if not DATA_DIR.exists():
            return migrated
        for directory in DATA_DIR.iterdir():
            if not directory.is_dir() or not directory.name.isdigit():
                continue
            event_id = directory.name
            meta = load_meta(event_id)
            if not meta or int(meta.get("ledger_schema_version") or 0) >= 2:
                continue
            initial_balance = _safe_float(
                meta.get(
                    "wallet_balance",
                    self.config.get("automated_wallet_balance", 100.0),
                ),
                100.0,
            )
            legacy_positions = [
                position
                for position in (meta.get("open_positions") or [])
                if isinstance(position, dict)
            ]
            if legacy_positions:
                meta["legacy_positions_quarantined"] = legacy_positions
            meta["legacy_available_balance"] = meta.get("available_balance")
            meta["open_positions"] = []
            meta["available_balance"] = initial_balance
            meta["wallet_balance"] = initial_balance
            meta["realized_pnl"] = 0.0
            meta["position_history"] = []
            meta["ledger_schema_version"] = 2
            meta["ledger_migrated_at"] = _utc_now_iso()
            self._save_analysis_meta(event_id, meta)
            migrated += 1
        return migrated

    def _event_score_history(self, event_id: str) -> list[str]:
        scores: list[str] = []
        for item in list_snapshot_files(event_id):
            try:
                snapshot = load_snapshot(event_id, item["file"])
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
            score = str((snapshot.get("flashscore") or {}).get("score") or "").strip()
            if score and (not scores or scores[-1] != score):
                scores.append(score)
        return scores

    def reconcile_finished_matches(self) -> int:
        """Cierra estados y liquida mercados demostrables (o void al cierre)."""
        reconciled = 0
        matches = load_index().get("matches") or {}
        pending: dict[str, dict[str, Any]] = {
            str(event_id): entry for event_id, entry in matches.items()
        }
        if DATA_DIR.exists():
            for directory in DATA_DIR.iterdir():
                if not directory.is_dir() or not directory.name.isdigit():
                    continue
                event_id = directory.name
                if event_id in pending:
                    continue
                meta = load_meta(event_id)
                if str(meta.get("analysis_status") or "") != "finished_unsettled":
                    continue
                pending[event_id] = {
                    "player1": meta.get("analysis_player1"),
                    "player2": meta.get("analysis_player2"),
                    "winner": None,
                    "finished_at": meta.get("settlement_finished_at") or _utc_now_iso(),
                    "is_finished": True,
                    "score": None,
                    "sets_won": None,
                    "competition": meta.get("analysis_tournament"),
                }

        for event_id, entry in pending.items():
            status = str(entry.get("status") or "").lower()
            meta = load_meta(event_id)
            scores = self._event_score_history(event_id)
            latest_score = scores[-1] if scores else entry.get("score")
            decided, sets_won, winner = match_decided_by_sets(
                entry,
                score=str(latest_score or "") or None,
                competition=entry.get("competition") or meta.get("analysis_tournament"),
            )
            if decided:
                if sets_won:
                    entry["sets_won"] = sets_won
                if winner:
                    entry["winner"] = winner
                if latest_score:
                    entry["score"] = latest_score
                entry["is_finished"] = True
                entry.setdefault("finished_at", entry.get("finished_at") or _utc_now_iso())

            is_finished = bool(
                entry.get("is_finished")
                or entry.get("finished_at")
                or decided
                or str(meta.get("analysis_status") or "") == "finished_unsettled"
                or any(
                    token in status
                    for token in ("final", "terminad", "finished", "retirad", "walkover")
                )
            )
            if not is_finished:
                continue
            with self._lock:
                if str(event_id) in self._processing:
                    continue
            with self._event_lock(str(event_id)):
                if self._reconcile_finished_match(str(event_id), entry):
                    reconciled += 1
        return reconciled

    def _reconcile_finished_match(
        self,
        event_id: str,
        entry: dict[str, Any],
    ) -> bool:
        meta = load_meta(event_id)
        open_positions = [
            position
            for position in (meta.get("open_positions") or [])
            if isinstance(position, dict)
        ]
        if (
            meta.get("settlement_finished_at") == entry.get("finished_at")
            and meta.get("analysis_status") == "finished"
            and not open_positions
        ):
            return False

        if not self._has_generalist_turns(event_id):
            self._ensure_terminal_wait_turn(
                event_id,
                entry,
                reason=(
                    "Partido finalizado sin turno de generalista; "
                    "Wait sintético para auditoría."
                ),
                snapshot_timestamp=str(
                    meta.get("last_processed_snapshot_at")
                    or meta.get("last_snapshot_at")
                    or entry.get("last_snapshot_at")
                    or ""
                )
                or None,
                label_source="finished_without_generalist",
            )
            meta = load_meta(event_id)

        unresolved: list[dict[str, Any]] = []
        history = list(meta.get("position_history") or [])
        available_balance = _safe_float(
            meta.get(
                "available_balance",
                meta.get(
                    "wallet_balance",
                    self.config.get("automated_wallet_balance", 100.0),
                ),
            ),
            100.0,
        )
        realized_pnl = _safe_float(meta.get("realized_pnl"), 0.0)
        scores = self._event_score_history(event_id)
        if entry.get("score"):
            entry_score = str(entry.get("score")).strip()
            if entry_score and (not scores or scores[-1] != entry_score):
                scores.append(entry_score)
        game_winners = build_game_winners_from_scores(scores)
        settle_entry = _enrich_entry_from_scores(
            {
                **entry,
                "player1": entry.get("player1") or meta.get("analysis_player1"),
                "player2": entry.get("player2") or meta.get("analysis_player2"),
            },
            scores,
        )
        if not settle_entry.get("winner"):
            decided, sets_won, winner = match_decided_by_sets(
                settle_entry,
                score=settle_entry.get("score") or (scores[-1] if scores else None),
                competition=settle_entry.get("competition") or entry.get("competition"),
            )
            if sets_won:
                settle_entry["sets_won"] = sets_won
            if winner:
                settle_entry["winner"] = winner
            elif decided:
                settle_entry["winner"] = winner_side(
                    sets_won,
                    competition=settle_entry.get("competition") or entry.get("competition"),
                )

        void_unresolved = bool(
            self.config.get("void_unresolved_markets_on_finish", True)
        )
        void_indecisive = bool(
            self.config.get("void_unresolved_on_indecisive_finish", True)
        )
        decisive = bool(
            settle_entry.get("winner") in {"player1", "player2"}
            or has_decisive_match_winner(
                settle_entry.get("sets_won"),
                competition=settle_entry.get("competition") or entry.get("competition"),
            )
        )
        finished_without_winner = bool(
            entry.get("finished_at") or entry.get("is_finished")
        ) and not decisive
        voided_any = False

        for position in open_positions:
            won = _settlement_result(
                position,
                settle_entry,
                game_winners=game_winners,
            )
            if won is None:
                # Solo anular cuando el partido está realmente decidido;
                # un false finished de Betfair no debe vaciar el ledger.
                if void_unresolved and decisive:
                    available_balance = _void_position(
                        position=position,
                        available_balance=available_balance,
                        history=history,
                        reason=(
                            "Mercado no demostrable al cierre del partido; "
                            "stake devuelto (void)."
                        ),
                    )
                    voided_any = True
                elif void_indecisive and finished_without_winner:
                    available_balance = _void_position(
                        position=position,
                        available_balance=available_balance,
                        history=history,
                        reason=(
                            "Partido cerrado sin ganador demostrable; "
                            "stake devuelto (void)."
                        ),
                    )
                    voided_any = True
                else:
                    unresolved.append(position)
                continue
            available_balance, realized_pnl = _apply_settled_position(
                position=position,
                won=won,
                available_balance=available_balance,
                realized_pnl=realized_pnl,
                history=history,
            )

        winner_side = settle_entry.get("winner") or entry.get("winner")
        winner_name = (
            (settle_entry.get("player1") or entry.get("player1"))
            if winner_side == "player1"
            else (settle_entry.get("player2") or entry.get("player2"))
            if winner_side == "player2"
            else meta.get("match_winner")
        )
        meta["open_positions"] = unresolved
        meta["position_history"] = history
        meta["available_balance"] = round(available_balance, 8)
        meta["realized_pnl"] = round(realized_pnl, 8)
        meta["match_winner"] = winner_name
        meta["settlement_finished_at"] = entry.get("finished_at") or meta.get(
            "settlement_finished_at"
        ) or _utc_now_iso()
        meta["settlement_status"] = (
            "settled" if not unresolved else "unresolved_markets"
        )
        meta["analysis_status"] = (
            "finished" if not unresolved else "finished_unsettled"
        )
        if voided_any:
            meta["settlement_voided_unresolved"] = True

        turns_path = match_dir(event_id) / "generalist_turns.jsonl"
        if turns_path.exists():
            updated_turns = []
            for line in turns_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                turn = json.loads(line)
                target = (turn.get("target") or {}).get("tool_call") or {}
                outcome = turn.setdefault("outcome", {})
                outcome["eventual_match_winner"] = winner_name
                outcome["pnl_after_match"] = (
                    round(realized_pnl, 8) if not unresolved else None
                )
                eligible = bool(
                    winner_name
                    and not unresolved
                    and not target.get("technical_fallback")
                    and not target.get("policy_rejected")
                )
                outcome["accepted_for_training"] = eligible
                outcome["label_source"] = (
                    "settled_match" if eligible else "pending_settlement"
                )
                updated_turns.append(json.dumps(turn, ensure_ascii=False))
            _atomic_write_text(
                turns_path,
                "\n".join(updated_turns) + ("\n" if updated_turns else ""),
            )

        self._save_analysis_meta(event_id, meta)
        try:
            prune_match_snapshots(event_id)
        except Exception:
            log.exception(
                "No se pudo podar snapshots tras settlement event_id=%s",
                event_id,
            )
        return True

    def _schedule_retry(
        self,
        event_id: str,
        entry: dict[str, Any],
        failure_count: int,
    ) -> None:
        with self._lock:
            if self._shutting_down:
                return
        delay = self._retry_delay(failure_count)

        def retry() -> None:
            with self._lock:
                self._retry_timers.pop(event_id, None)
            try:
                self.submit_snapshot(event_id, {}, entry)
            except RuntimeError:
                log.info("Retry cancelado durante shutdown event_id=%s", event_id)

        timer = threading.Timer(delay, retry)
        timer.daemon = True
        with self._lock:
            if self._shutting_down:
                return
            previous = self._retry_timers.pop(event_id, None)
            if previous:
                previous.cancel()
            self._retry_timers[event_id] = timer
        timer.start()
        log.warning(
            "Análisis reprogramado event_id=%s en %ss (fallo=%s)",
            event_id,
            delay,
            failure_count,
        )

    def _retry_delay(self, failure_count: int) -> int:
        base_delay = max(
            5,
            int(self.config.get("analysis_retry_delay_sec", 60)),
        )
        return min(900, base_delay * (2 ** min(max(0, failure_count - 1), 4)))

    def _mark_snapshots_superseded(
        self,
        event_id: str,
        snapshots: list[dict[str, str]],
        *,
        reason: str,
        status: str,
    ) -> None:
        if not snapshots:
            return
        with self._event_lock(event_id):
            current_meta = load_meta(event_id)
            history = list(
                current_meta.get("analysis_superseded_batches") or []
            )
            history.append(
                {
                    "recorded_at": _utc_now_iso(),
                    "reason": reason,
                    "count": len(snapshots),
                    "first_snapshot_at": snapshots[0].get("timestamp"),
                    "last_snapshot_at": snapshots[-1].get("timestamp"),
                }
            )
            current_meta["analysis_superseded_batches"] = history[-200:]
            current_meta["last_processed_snapshot_at"] = snapshots[-1]["timestamp"]
            current_meta["analysis_status"] = status
            for key in (
                "analysis_error",
                "analysis_error_at",
                "analysis_failure_snapshot_at",
                "analysis_failure_count",
                "analysis_next_retry_at",
                "analysis_current_snapshot_at",
                "analysis_current_started_at",
            ):
                current_meta.pop(key, None)
            self._save_analysis_meta(
                event_id,
                current_meta,
                remove_keys=(
                    "analysis_error",
                    "analysis_error_at",
                    "analysis_failure_snapshot_at",
                    "analysis_failure_count",
                    "analysis_next_retry_at",
                    "analysis_current_snapshot_at",
                    "analysis_current_started_at",
                ),
            )

    def _has_generalist_turns(self, event_id: str) -> bool:
        turns_path = match_dir(event_id) / "generalist_turns.jsonl"
        try:
            return turns_path.exists() and turns_path.stat().st_size > 0
        except OSError:
            return False

    def _ensure_terminal_wait_turn(
        self,
        event_id: str,
        entry: dict[str, Any],
        *,
        reason: str,
        snapshot_timestamp: str | None,
        label_source: str,
    ) -> bool:
        """Garantiza al menos un Wait en journal cuando el partido cierra sin turn."""
        if self._has_generalist_turns(event_id):
            return False
        meta = load_meta(event_id)
        player1 = str(
            meta.get("analysis_player1") or entry.get("player1") or "Player A"
        )
        player2 = str(
            meta.get("analysis_player2") or entry.get("player2") or "Player B"
        )
        tournament = str(
            meta.get("analysis_tournament")
            or entry.get("competition")
            or "Unknown"
        )
        match_date = str(meta.get("analysis_match_date") or "unknown")
        ts = datetime.now().astimezone().isoformat(timespec="seconds")
        slug_a = re.sub(r"[^a-z0-9]+", "_", player1.casefold()).strip("_") or "a"
        slug_b = re.sub(r"[^a-z0-9]+", "_", player2.casefold()).strip("_") or "b"
        trajectory_id = f"match_{match_date}_{slug_a}_vs_{slug_b}"
        record = {
            "schema_version": "tennis_generalist_turn_v1",
            "trajectory_id": trajectory_id,
            "turn_id": f"{trajectory_id}_tick_0000",
            "step_index": 0,
            "timestamp": ts,
            "match": {
                "player_a": player1,
                "player_b": player2,
                "tournament": tournament,
                "match_date": match_date,
            },
            "state": {
                "wallet_balance": _safe_float(
                    meta.get(
                        "wallet_balance",
                        self.config.get("automated_wallet_balance", 100.0),
                    ),
                    100.0,
                ),
                "available_balance": _safe_float(
                    meta.get(
                        "available_balance",
                        meta.get(
                            "wallet_balance",
                            self.config.get("automated_wallet_balance", 100.0),
                        ),
                    ),
                    100.0,
                ),
                "previous_actions": meta.get("previous_actions") or [],
                "open_positions": meta.get("open_positions") or [],
            },
            "input": {
                "reports": {},
                "market_snapshot": {
                    "snapshot_timestamp": snapshot_timestamp,
                },
            },
            "target": {
                "tool_call": {
                    "name": "wait",
                    "technical_fallback": False,
                    "synthetic": True,
                    "arguments": {
                        "reason": reason,
                        "confidence": 1.0,
                        "next_trigger": (
                            "Partido cerrado sin turno de generalista en vivo."
                        ),
                        "notes": f"Wait sintético ({label_source}).",
                    },
                }
            },
            "outcome": {
                "accepted_for_training": False,
                "label_source": label_source,
                "eventual_match_winner": meta.get("match_winner")
                or entry.get("winner"),
                "pnl_after_match": None,
            },
        }
        turns_path = match_dir(event_id) / "generalist_turns.jsonl"
        _save_turn_log(record, str(turns_path))
        try:
            decision = format_decision_display(record)
        except Exception:
            decision = (
                f"Wait (sintético): {reason}\n"
                f"label_source={label_source}"
            )
        _atomic_write_text(match_dir(event_id) / "decision.md", str(decision))
        meta["last_decision"] = decision
        meta["last_analysis_at"] = _utc_now_iso()
        meta["last_analysis_step"] = 0
        self._save_analysis_meta(event_id, meta)
        log.info(
            "Wait sintético escrito event_id=%s label=%s",
            event_id,
            label_source,
        )
        return True

    def _drain_event(self, event_id: str) -> None:
        try:
            while True:
                with self._lock:
                    entry = self._pending.get(event_id)
                if entry is None:
                    break

                meta = load_meta(event_id)
                with self._lock:
                    circuit_until = self._provider_circuit_until
                if (
                    circuit_until is not None
                    and circuit_until > datetime.now(timezone.utc)
                ):
                    with self._lock:
                        self._pending.pop(event_id, None)
                        has_timer = event_id in self._retry_timers
                    if not has_timer:
                        self._schedule_retry(
                            event_id,
                            entry,
                            int(meta.get("analysis_failure_count") or 5),
                        )
                    return
                next_retry_at = meta.get("analysis_next_retry_at")
                if next_retry_at:
                    try:
                        next_retry = datetime.fromisoformat(
                            str(next_retry_at).replace("Z", "+00:00")
                        )
                        if next_retry.tzinfo is None:
                            next_retry = next_retry.replace(tzinfo=timezone.utc)
                    except ValueError:
                        next_retry = None
                    if next_retry and next_retry > datetime.now(timezone.utc):
                        with self._lock:
                            self._pending.pop(event_id, None)
                            has_timer = event_id in self._retry_timers
                        if not has_timer:
                            self._schedule_retry(
                                event_id,
                                entry,
                                int(meta.get("analysis_failure_count") or 1),
                            )
                        return
                last_processed = meta.get("last_processed_snapshot_at")
                snapshots = list_snapshot_files(event_id)
                pending = [
                    item for item in snapshots
                    if item.get("timestamp")
                    and (
                        not last_processed
                        or str(item["timestamp"]) > str(last_processed)
                    )
                ]
                if not pending:
                    with self._lock:
                        self._pending.pop(event_id, None)
                    break

                latest = pending[-1]
                latest_timestamp = str(latest.get("timestamp") or "")
                try:
                    latest_dt = datetime.fromisoformat(
                        latest_timestamp.replace("Z", "+00:00")
                    )
                    if latest_dt.tzinfo is None:
                        latest_dt = latest_dt.replace(tzinfo=timezone.utc)
                    latest_age = (
                        datetime.now(timezone.utc) - latest_dt
                    ).total_seconds()
                except ValueError:
                    latest_age = float("inf")
                status_text = str(entry.get("status") or "").casefold()
                entry_finished = bool(
                    entry.get("is_finished")
                    or entry.get("finished_at")
                    or any(
                        token in status_text
                        for token in (
                            "final",
                            "terminad",
                            "finished",
                            "retirad",
                            "walkover",
                        )
                    )
                )
                max_age = int(
                    self.config.get("analysis_snapshot_max_age_sec", 300)
                )
                if entry_finished or latest_age > max_age:
                    age_description = (
                        "antigüedad desconocida"
                        if latest_age == float("inf")
                        else f"{int(latest_age)}s de antigüedad"
                    )
                    reason = (
                        "El partido terminó antes de analizar el backlog."
                        if entry_finished
                        else (
                            f"Snapshot más reciente con {age_description}; "
                            f"máximo={max_age}s."
                        )
                    )
                    skip_status = (
                        "finished_unanalyzed" if entry_finished else "stale_skipped"
                    )
                    if entry_finished:
                        # Último intento: analizar el snapshot más reciente
                        # antes de cerrar sin turno de generalista.
                        try:
                            last_snapshot = load_snapshot(
                                event_id, latest["file"]
                            )
                            self._process_snapshot(
                                event_id,
                                last_snapshot,
                                entry,
                                latest_timestamp,
                            )
                            older = [
                                item
                                for item in pending
                                if item.get("timestamp") != latest_timestamp
                            ]
                            if older:
                                self._mark_snapshots_superseded(
                                    event_id,
                                    older,
                                    reason=(
                                        "Backlog previo al último snapshot "
                                        "analizado al cierre."
                                    ),
                                    status="coalesced",
                                )
                            continue
                        except Exception as exc:
                            log.warning(
                                "Último análisis al cierre falló "
                                "event_id=%s: %s",
                                event_id,
                                exc,
                            )
                        self._ensure_terminal_wait_turn(
                            event_id,
                            entry,
                            reason=reason,
                            snapshot_timestamp=latest_timestamp,
                            label_source=skip_status,
                        )
                    self._mark_snapshots_superseded(
                        event_id,
                        pending,
                        reason=reason,
                        status=skip_status,
                    )
                    continue
                if len(pending) > 1:
                    self._mark_snapshots_superseded(
                        event_id,
                        pending[:-1],
                        reason=(
                            "Backlog coalescido: solo el snapshot live más "
                            "reciente puede mutar el ledger."
                        ),
                        status="coalesced",
                    )
                    pending = [latest]

                snapshot_info = pending[0]
                snapshot_timestamp = snapshot_info["timestamp"]
                try:
                    snapshot = load_snapshot(event_id, snapshot_info["file"])
                    success = False
                    error: Exception | None = None
                    for attempt in range(3):
                        try:
                            self._process_snapshot(
                                event_id,
                                snapshot,
                                entry,
                                snapshot_timestamp,
                            )
                            success = True
                            break
                        except Exception as exc:
                            error = exc
                            if isinstance(exc, AnalysisDeferredError):
                                break
                            if attempt < 2:
                                time.sleep(2 ** attempt)
                    if not success and error is not None:
                        raise error
                except Exception as exc:
                    meta = load_meta(event_id)
                    error_text = str(exc).casefold()
                    infrastructure_error = bool(
                        "insufficient_quota" in error_text
                        or "error code: 429" in error_text
                        or "current quota" in error_text
                        or "rate_limit" in error_text
                        or "too many requests" in error_text
                    )
                    if infrastructure_error:
                        circuit_seconds = int(
                            self.config.get(
                                "provider_circuit_breaker_sec",
                                900,
                            )
                        )
                        with self._lock:
                            self._provider_circuit_until = (
                                datetime.now(timezone.utc)
                                + timedelta(seconds=circuit_seconds)
                            )
                    previous_failure_snapshot = meta.get("analysis_failure_snapshot_at")
                    failure_count = (
                        int(meta.get("analysis_failure_count") or 0) + 1
                        if previous_failure_snapshot == snapshot_timestamp
                        else 1
                    )
                    meta["analysis_status"] = "error"
                    meta["analysis_error"] = str(exc)
                    meta["analysis_error_at"] = _utc_now_iso()
                    meta["analysis_failure_snapshot_at"] = snapshot_timestamp
                    meta["analysis_failure_count"] = failure_count
                    max_failures = int(
                        self.config.get(
                            "analysis_max_failures_per_snapshot",
                            12,
                        )
                    )
                    if not infrastructure_error and failure_count >= max_failures:
                        dead_letter = {
                            "recorded_at": _utc_now_iso(),
                            "snapshot_at": snapshot_timestamp,
                            "snapshot_file": snapshot_info.get("file"),
                            "attempts": failure_count,
                            "error": str(exc),
                        }
                        dead_letters = list(meta.get("analysis_dead_letters") or [])
                        dead_letters.append(dead_letter)
                        meta["analysis_dead_letters"] = dead_letters[-200:]
                        meta["analysis_status"] = "dead_letter"
                        meta["last_processed_snapshot_at"] = snapshot_timestamp
                        dead_letter_path = (
                            match_dir(event_id)
                            / "dead_letters"
                            / f"{str(snapshot_timestamp).replace(':', '-')}.json"
                        )
                        _atomic_write_text(
                            dead_letter_path,
                            json.dumps(
                                dead_letter,
                                ensure_ascii=False,
                                indent=2,
                            ),
                        )
                        self._save_analysis_meta(
                            event_id,
                            meta,
                            remove_keys=(
                                "analysis_next_retry_at",
                                "analysis_current_snapshot_at",
                                "analysis_current_started_at",
                            ),
                        )
                        log.error(
                            "Snapshot enviado a dead-letter event_id=%s snapshot=%s",
                            event_id,
                            snapshot_timestamp,
                        )
                        continue
                    retry_delay = self._retry_delay(failure_count)
                    meta["analysis_next_retry_at"] = (
                        datetime.now(timezone.utc)
                        + timedelta(seconds=retry_delay)
                    ).isoformat()
                    meta.pop("analysis_current_snapshot_at", None)
                    meta.pop("analysis_current_started_at", None)
                    self._save_analysis_meta(
                        event_id,
                        meta,
                        remove_keys=(
                            "analysis_current_snapshot_at",
                            "analysis_current_started_at",
                        ),
                    )
                    with self._lock:
                        self._pending.pop(event_id, None)
                    log.exception("Error analizando event_id=%s", event_id)
                    self._schedule_retry(event_id, entry, failure_count)
                    return
        finally:
            with self._lock:
                self._processing.discard(event_id)
                # Evita perder un snapshot que haya llegado entre el pop y el
                # final del worker.
                if event_id in self._pending:
                    self._processing.add(event_id)
                    try:
                        self._executor.submit(self._drain_event, event_id)
                    except RuntimeError:
                        self._processing.discard(event_id)

    def _context_path(self, event_id: str) -> Path:
        return match_dir(event_id) / "context.md"

    def _reports_dir(self, event_id: str) -> Path:
        path = match_dir(event_id) / "reports"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _load_reports(self, event_id: str) -> dict[str, str]:
        reports: dict[str, str] = {}
        reports_dir = self._reports_dir(event_id)
        for key in REPORT_KEYS:
            path = reports_dir / f"{key}.md"
            if path.exists():
                try:
                    reports[key] = path.read_text(encoding="utf-8")
                except OSError:
                    pass
        return reports

    def _save_reports(self, event_id: str, result: dict[str, Any]) -> dict[str, str]:
        reports = {}
        reports_dir = self._reports_dir(event_id)
        for key in REPORT_KEYS:
            content = result.get(key)
            if not content:
                continue
            text = sanitize_analyst_report(str(content))
            _atomic_write_text(reports_dir / f"{key}.md", text)
            reports[key] = text
        return reports

    def _report_quality_errors(
        self,
        reports: dict[str, str],
    ) -> dict[str, str]:
        errors: dict[str, str] = {}
        minimum = int(self.config.get("analyst_report_min_chars", 1000))
        failure_markers = (
            "insufficient_quota",
            "error code: 429",
            "no puedo proporcionar",
            "no tengo información",
            "no hay datos meteorológicos disponibles",
            "no es posible evaluar",
        )
        for key in REPORT_KEYS:
            text = str(reports.get(key) or "").strip()
            if not text:
                errors[key] = "Informe ausente."
                continue
            if "## Información verificada del torneo" in text:
                lowered = text.casefold()
                marker = next(
                    (item for item in failure_markers if item in lowered),
                    None,
                )
                if marker:
                    errors[key] = f"Informe contiene señal de fallo: {marker}."
                continue
            if len(text) < minimum:
                errors[key] = (
                    f"Informe demasiado corto ({len(text)} < {minimum} caracteres)."
                )
                continue
            lowered = text.casefold()
            marker = next(
                (item for item in failure_markers if item in lowered),
                None,
            )
            if marker:
                errors[key] = f"Informe contiene señal de fallo: {marker}."
        return errors

    def _tool_log_offset(self) -> int:
        path = Path(str(self.config.get("tool_outputs_log") or ""))
        try:
            return path.stat().st_size
        except OSError:
            return 0

    def _tool_infrastructure_errors_since(self, offset: int) -> list[str]:
        path = Path(str(self.config.get("tool_outputs_log") or ""))
        if not path.exists():
            return []
        try:
            size = path.stat().st_size
            with path.open("rb") as tool_log:
                tool_log.seek(offset if offset <= size else 0)
                payload = tool_log.read().decode("utf-8", errors="replace")
        except OSError:
            return []
        errors = []
        for line in payload.splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            output = str(item.get("output") or "")
            lowered = output.casefold()
            if (
                "insufficient_quota" in lowered
                or "error code: 429" in lowered
                or "current quota" in lowered
                or "rate_limit" in lowered
                or "too many requests" in lowered
            ):
                errors.append(output[:500])
        return errors[:5]

    def _resolve_tournament_identity(
        self,
        snapshot: dict[str, Any],
        entry: dict[str, Any],
        meta: dict[str, Any] | None = None,
    ):
        betfair = snapshot.get("betfair") or {}
        flashscore_match = (snapshot.get("flashscore") or {}).get("match") or {}
        meta = meta or {}
        return resolve_tournament_identity(
            betfair_competition=entry.get("competition") or betfair.get("competition"),
            flashscore_tournament=flashscore_match.get("tournament"),
            stored=meta.get("analysis_tournament"),
        )

    def _tournament_identity_drift(
        self,
        meta: dict[str, Any],
        identity,
    ) -> bool:
        """True si los informes completados ya no coinciden con el torneo resuelto."""
        previous_surface = meta.get("analysis_tournament_surface")
        previous_label = meta.get("analysis_tournament")
        if (
            previous_label
            and identity.display_name
            and previous_label != identity.display_name
        ):
            return True
        if not identity.surface:
            return False
        if previous_surface and previous_surface != identity.surface:
            return True
        if not previous_surface:
            inferred = normalize_tournament(previous_label or "").surface
            if inferred and inferred != identity.surface:
                return True
            if not inferred:
                return True
        return False

    def _sync_analysis_tournament(
        self,
        meta: dict[str, Any],
        identity,
    ) -> bool:
        """Actualiza torneo almacenado; devuelve True si cambió superficie o etiqueta."""
        previous_surface = meta.get("analysis_tournament_surface")
        previous_label = meta.get("analysis_tournament")
        changed_surface = bool(
            identity.surface
            and (
                (previous_surface and previous_surface != identity.surface)
                or (not previous_surface and meta.get("analysts_completed"))
            )
        )
        changed_label = bool(
            previous_label
            and identity.display_name
            and previous_label != identity.display_name
        )
        if previous_label != identity.display_name or not meta.get("analysis_tournament"):
            meta["analysis_tournament"] = identity.display_name
        if identity.surface:
            meta["analysis_tournament_surface"] = identity.surface
        return changed_surface or changed_label

    def _match_details(
        self,
        snapshot: dict[str, Any],
        entry: dict[str, Any],
        meta: dict[str, Any] | None = None,
    ) -> tuple[str, str, str, str]:
        betfair = snapshot.get("betfair") or {}
        flashscore = snapshot.get("flashscore") or {}
        flashscore_match = flashscore.get("match") or {}
        player1 = entry.get("player1") or betfair.get("player1") or flashscore.get("player1") or ""
        player2 = entry.get("player2") or betfair.get("player2") or flashscore.get("player2") or ""
        identity = self._resolve_tournament_identity(snapshot, entry, meta)
        timestamp = str(snapshot.get("timestamp") or _utc_now_iso())
        match_date = timestamp[:10]
        return str(player1), str(player2), identity.display_name, match_date

    def _build_state(
        self,
        event_id: str,
        snapshot: dict[str, Any],
        entry: dict[str, Any],
        meta: dict[str, Any],
        reports: dict[str, str],
    ) -> dict[str, Any]:
        player1, player2, tournament, match_date = self._match_details(snapshot, entry, meta)
        player1 = str(meta.get("analysis_player1") or player1)
        player2 = str(meta.get("analysis_player2") or player2)
        betfair = snapshot.get("betfair") or {}
        flashscore_match = (snapshot.get("flashscore") or {}).get("match") or {}
        identity = self._resolve_tournament_identity(snapshot, entry, meta)
        tournament = identity.display_name
        match_date = str(meta.get("analysis_match_date") or match_date)
        context_path = self._context_path(event_id)
        turns_path = match_dir(event_id) / "generalist_turns.jsonl"
        graph = self._get_graph()
        state = graph.propagator.create_initial_state(
            player1,
            player2,
            match_date,
            tournament,
            _safe_float(
                meta.get(
                    "wallet_balance",
                    self.config.get("automated_wallet_balance", 100.0),
                ),
                _safe_float(self.config.get("automated_wallet_balance"), 100.0),
            ),
            context_path=str(context_path),
            betfair_competition=entry.get("competition") or betfair.get("competition"),
            flashscore_tournament=flashscore_match.get("tournament"),
        )

        betfair = snapshot.get("betfair") or {}
        flashscore = snapshot.get("flashscore") or {}
        is_live = bool(betfair.get("is_live") or entry.get("is_live"))
        state.update(
            {
                **reports,
                "scraper_snapshot": snapshot,
                "context_path": str(context_path),
                "generalist_turns_log": str(turns_path),
                "defer_generalist_persistence": True,
                "step_index": int(meta.get("last_analysis_step", -1)) + 1,
                "phase": "live" if is_live else "post_match",
                "score": flashscore.get("score") or entry.get("score") or "",
                "current_set": flashscore.get("current_game"),
                "server": flashscore.get("serving") or "",
                "game_score": flashscore.get("current_points") or "",
                "elapsed_minutes": None,
                "previous_actions": meta.get("previous_actions") or [],
                "open_positions": meta.get("open_positions") or [],
                "available_balance": _safe_float(
                    meta.get(
                        "available_balance",
                        meta.get("wallet_balance", self.config.get("automated_wallet_balance", 100.0)),
                    ),
                    _safe_float(self.config.get("automated_wallet_balance"), 100.0),
                ),
            }
        )
        return state

    def _prepare_commit(
        self,
        event_id: str,
        cursor_timestamp: str,
        snapshot: dict[str, Any],
        meta: dict[str, Any],
        record: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Valida y aplica una acción sobre una copia de meta."""
        committed_meta = deepcopy(meta)
        committed_record = deepcopy(record)
        target = (committed_record.get("target") or {}).get("tool_call") or {}
        args = target.get("arguments") or {}
        name = str(target.get("name") or "wait").lower()
        original_call = deepcopy(target)
        action_timestamp = _utc_now_iso()

        previous = [
            previous_action
            for previous_action in (committed_meta.get("previous_actions") or [])
            if isinstance(previous_action, dict)
        ]
        positions = [
            position
            for position in (committed_meta.get("open_positions") or [])
            if isinstance(position, dict)
        ]
        match = committed_record.get("match") or {}
        match_id = (
            f"{match.get('player_a', '')} vs {match.get('player_b', '')} | "
            f"{match.get('tournament', '')} | {match.get('match_date', '')}"
        )
        initial_balance = _safe_float(
            committed_meta.get(
                "wallet_balance",
                self.config.get("automated_wallet_balance", 100.0),
            ),
            100.0,
        )
        available_balance = _safe_float(
            committed_meta.get("available_balance", initial_balance),
            initial_balance,
        )
        committed_meta.setdefault("wallet_balance", initial_balance)
        committed_meta["ledger_schema_version"] = 2

        def reject(reason: str) -> tuple[dict[str, Any], dict[str, Any]]:
            rejected_record = _policy_wait(
                committed_record,
                reason,
                original_call,
            )
            rejected_action = {
                "timestamp": action_timestamp,
                "tool": f"{name}_rejected",
                "execution_status": "rejected",
                "args": {
                    "match_id": match_id,
                    "reason": reason,
                    "original_tool_call": original_call,
                },
            }
            previous.append(rejected_action)
            committed_meta["previous_actions"] = previous[-200:]
            committed_meta["last_action"] = rejected_action
            committed_meta["last_policy_rejection"] = rejected_action
            committed_meta["open_positions"] = positions
            committed_meta["available_balance"] = available_balance
            return committed_meta, rejected_record

        if target.get("policy_rejected"):
            original = target.get("original_tool_call") or {}
            rejection_reason = str(args.get("reason") or "Acción rechazada.")
            rejected_action = {
                "timestamp": action_timestamp,
                "tool": f"{str(original.get('name') or 'action').lower()}_rejected",
                "execution_status": "rejected",
                "args": {
                    "match_id": match_id,
                    "reason": rejection_reason,
                    "original_tool_call": original,
                },
            }
            previous.append(rejected_action)
            committed_meta["previous_actions"] = previous[-200:]
            committed_meta["last_action"] = rejected_action
            committed_meta["last_policy_rejection"] = rejected_action
            committed_meta["open_positions"] = positions
            committed_meta["available_balance"] = available_balance
            return committed_meta, committed_record

        confidence = args.get("confidence")
        if confidence is not None and not 0.0 <= _safe_float(confidence, -1.0) <= 1.0:
            return reject("confidence debe estar entre 0 y 1.")

        if name == "bet":
            tradeable, reason = _snapshot_tradeable(snapshot)
            if not tradeable:
                return reject(reason)
            stake = _safe_float(args.get("stake"), 0.0)
            if stake <= 0:
                return reject("El stake debe ser mayor que cero.")
            minimum_stake = _safe_float(
                self.config.get("minimum_bet_stake"),
                1.0,
            )
            if stake + 1e-9 < minimum_stake:
                return reject(
                    f"Stake {stake:.2f} inferior al mínimo "
                    f"{minimum_stake:.2f}."
                )
            if stake > available_balance:
                return reject(
                    f"Stake {stake:.2f} superior al saldo disponible "
                    f"{available_balance:.2f}."
                )
            max_stake_fraction = _safe_float(
                self.config.get("max_stake_fraction"),
                0.20,
            )
            if 0.0 < max_stake_fraction < 1.0:
                max_stake = initial_balance * max_stake_fraction
                if stake > max_stake + 1e-9:
                    return reject(
                        f"Stake {stake:.2f} supera el tope de diversificación "
                        f"({max_stake_fraction:.0%} del wallet = {max_stake:.2f})."
                    )
            exposure = sum(
                _safe_float(position.get("remaining_stake"), 0.0)
                for position in positions
            )
            max_exposure_fraction = _safe_float(
                self.config.get("max_total_exposure_fraction"),
                0.50,
            )
            if 0.0 < max_exposure_fraction <= 1.0:
                max_exposure = initial_balance * max_exposure_fraction
                if exposure + stake > max_exposure + 1e-9:
                    return reject(
                        f"Exposición total {exposure + stake:.2f} supera el tope "
                        f"({max_exposure_fraction:.0%} del wallet = "
                        f"{max_exposure:.2f})."
                    )
            market, runner = _market_selection(
                snapshot,
                str(args.get("market") or ""),
                str(args.get("option") or ""),
            )
            if not market or not runner:
                return reject("Mercado o selección ausentes del snapshot.")
            if str(market.get("status") or "").upper() != "OPEN":
                return reject("El mercado no está abierto.")
            if str(runner.get("status") or "").upper() not in {"", "ACTIVE"}:
                return reject("La selección no está activa.")
            odds = _safe_float(runner.get("odds_decimal"), 0.0)
            if odds <= 1.0:
                return reject("La cuota decimal no es válida.")
            estimated_probability = _safe_float(
                args.get("estimated_probability"),
                -1.0,
            )
            if not 0.0 < estimated_probability < 1.0:
                return reject(
                    "Bet requiere estimated_probability entre 0 y 1."
                )
            implied_probability = 1.0 / odds
            edge = estimated_probability - implied_probability
            minimum_edge = _safe_float(
                self.config.get("minimum_bet_edge"),
                0.02,
            )
            market_type = str(market.get("market_type") or args.get("market") or "")
            family = _market_family(market_type)
            short_odds_max = _safe_float(
                self.config.get("match_odds_short_odds_max"),
                1.25,
            )
            short_min_edge = _safe_float(
                self.config.get("match_odds_short_min_edge"),
                0.05,
            )
            if (
                family == "match_odds"
                and odds <= short_odds_max
                and short_min_edge > minimum_edge
            ):
                minimum_edge = short_min_edge
            if edge < minimum_edge:
                return reject(
                    f"Edge insuficiente: estimada={estimated_probability:.4f}, "
                    f"implícita={implied_probability:.4f}, edge={edge:.4f}, "
                    f"mínimo={minimum_edge:.4f}"
                    + (
                        f" (MATCH_ODDS corto <= {short_odds_max:.2f})."
                        if family == "match_odds" and odds <= short_odds_max
                        else "."
                    )
                )

            position_id = (
                f"{event_id}:{cursor_timestamp}:"
                f"{runner.get('selection_id') or len(positions) + 1}"
            )
            calibration = _bet_calibration_fields(
                stake=stake,
                odds=odds,
                estimated_probability=estimated_probability,
                wallet_balance=initial_balance,
                available_balance=available_balance,
                market=market_type,
            )
            args.update(
                {
                    "match_id": match_id,
                    "market_id": market.get("market_id"),
                    "selection_id": runner.get("selection_id"),
                    "odds": odds,
                    "estimated_probability": estimated_probability,
                    "implied_probability": implied_probability,
                    "edge": edge,
                    "stake": stake,
                    "position_id": position_id,
                    "stake_pct_wallet": calibration.get("stake_pct_wallet"),
                    "stake_pct_available": calibration.get("stake_pct_available"),
                    "market_family": family,
                }
            )
            position = {
                "position_id": position_id,
                "match_id": match_id,
                "selection": runner.get("name"),
                "selection_id": runner.get("selection_id"),
                "market": market.get("market_type"),
                "market_id": market.get("market_id"),
                "entry_odds": odds,
                "initial_stake": stake,
                "remaining_stake": stake,
                "opened_at": action_timestamp,
                "snapshot_at": cursor_timestamp,
            }
            positions.append(position)
            available_balance -= stake
            history = list(committed_meta.get("position_history") or [])
            history.append({"event": "opened", **position})
            committed_meta["position_history"] = history
        elif name == "close":
            close_percentage = _safe_float(args.get("close_percentage"), 0.0)
            if not 0.0 < close_percentage <= 1.0:
                return reject("close_percentage debe estar entre 0 y 1.")
            position_id = str(args.get("position_id") or "")
            candidates = [
                position
                for position in positions
                if (
                    position.get("position_id") == position_id
                    if position_id
                    else position.get("match_id") == (args.get("match_id") or match_id)
                )
            ]
            if len(candidates) != 1:
                return reject(
                    "Close requiere un position_id exacto y no ambiguo."
                )
            position = candidates[0]
            market, runner = _market_selection(
                snapshot,
                str(position.get("market") or ""),
                str(position.get("selection") or ""),
                market_id=str(position.get("market_id") or "") or None,
                selection_id=position.get("selection_id"),
            )
            if not market or not runner:
                # Si el mercado ya no cotiza, intenta liquidar por marcador
                # (p.ej. juego ya resuelto) en lugar de dejar la posición huérfana.
                scores = []
                score = str((snapshot.get("flashscore") or {}).get("score") or "").strip()
                if score:
                    scores.append(score)
                scores = [
                    *self._event_score_history(event_id),
                    *scores,
                ]
                # Deduplicar preservando orden.
                deduped: list[str] = []
                for item in scores:
                    if item and (not deduped or deduped[-1] != item):
                        deduped.append(item)
                game_winners = build_game_winners_from_scores(deduped)
                settle_entry = _enrich_entry_from_scores(
                    {
                        "player1": committed_meta.get("analysis_player1")
                        or (snapshot.get("betfair") or {}).get("player1"),
                        "player2": committed_meta.get("analysis_player2")
                        or (snapshot.get("betfair") or {}).get("player2"),
                        "score": score,
                        "winner": (snapshot.get("flashscore") or {}).get("winner"),
                        "sets_won": (snapshot.get("flashscore") or {}).get("sets_won"),
                    },
                    deduped,
                )
                won = _settlement_result(
                    position,
                    settle_entry,
                    game_winners=game_winners,
                )
                if won is None:
                    return reject(
                        "No existe una cuota actual para cerrar la posición; "
                        "se mantiene abierta hasta liquidación."
                    )
                remaining_stake = _safe_float(
                    position.get("remaining_stake", position.get("initial_stake")),
                    0.0,
                )
                closed_stake = remaining_stake * close_percentage
                entry_odds = _safe_float(position.get("entry_odds"), 0.0)
                realized_pnl = (
                    closed_stake * (entry_odds - 1.0) if won else -closed_stake
                )
                payout = closed_stake * entry_odds if won else 0.0
                available_balance += payout
                args.update(
                    {
                        "match_id": match_id,
                        "position_id": position["position_id"],
                        "close_percentage": close_percentage,
                        "entry_odds": entry_odds,
                        "exit_odds": None,
                        "closed_stake": closed_stake,
                        "realized_pnl": realized_pnl,
                        "settled_without_quote": True,
                        "won": won,
                    }
                )
                remaining_after = remaining_stake - closed_stake
                if remaining_after <= 1e-9:
                    positions = [
                        item
                        for item in positions
                        if item.get("position_id") != position.get("position_id")
                    ]
                else:
                    position["remaining_stake"] = remaining_after
                committed_meta["realized_pnl"] = _safe_float(
                    committed_meta.get("realized_pnl"),
                    0.0,
                ) + realized_pnl
                history = list(committed_meta.get("position_history") or [])
                history.append(
                    {
                        "event": "settled_on_close",
                        "position_id": position["position_id"],
                        "closed_at": action_timestamp,
                        "close_percentage": close_percentage,
                        "closed_stake": closed_stake,
                        "entry_odds": entry_odds,
                        "won": won,
                        "realized_pnl": realized_pnl,
                    }
                )
                committed_meta["position_history"] = history
            else:
                exit_odds = _safe_float(runner.get("odds_decimal"), 0.0)
                entry_odds = _safe_float(position.get("entry_odds"), 0.0)
                remaining_stake = _safe_float(
                    position.get("remaining_stake", position.get("initial_stake")),
                    0.0,
                )
                if exit_odds <= 1.0 or entry_odds <= 1.0 or remaining_stake <= 0:
                    return reject("La posición no contiene cuotas o stake válidos.")

                closed_stake = remaining_stake * close_percentage
                realized_pnl = closed_stake * ((entry_odds / exit_odds) - 1.0)
                available_balance += closed_stake + realized_pnl
                args.update(
                    {
                        "match_id": match_id,
                        "position_id": position["position_id"],
                        "close_percentage": close_percentage,
                        "entry_odds": entry_odds,
                        "exit_odds": exit_odds,
                        "closed_stake": closed_stake,
                        "realized_pnl": realized_pnl,
                    }
                )
                remaining_after = remaining_stake - closed_stake
                if remaining_after <= 1e-9:
                    positions = [
                        item
                        for item in positions
                        if item.get("position_id") != position.get("position_id")
                    ]
                else:
                    position["remaining_stake"] = remaining_after
                committed_meta["realized_pnl"] = _safe_float(
                    committed_meta.get("realized_pnl"),
                    0.0,
                ) + realized_pnl
                history = list(committed_meta.get("position_history") or [])
                history.append(
                    {
                        "event": "closed",
                        "position_id": position["position_id"],
                        "closed_at": action_timestamp,
                        "close_percentage": close_percentage,
                        "closed_stake": closed_stake,
                        "entry_odds": entry_odds,
                        "exit_odds": exit_odds,
                        "realized_pnl": realized_pnl,
                    }
                )
                committed_meta["position_history"] = history
        elif name != "wait":
            return reject(f"Tool desconocida: {name}.")

        action = {
            "timestamp": action_timestamp,
            "tool": name,
            "execution_status": "accepted",
            "args": {"match_id": match_id, **args},
        }
        previous.append(action)
        committed_meta["previous_actions"] = previous[-200:]
        committed_meta["open_positions"] = positions
        committed_meta["available_balance"] = round(available_balance, 8)
        committed_meta["last_action"] = action
        return committed_meta, committed_record

    def _journal_path(self, event_id: str, cursor_timestamp: str) -> Path:
        safe_timestamp = (
            str(cursor_timestamp)
            .replace(":", "-")
            .replace("+", "_")
            .replace("/", "-")
        )
        return match_dir(event_id) / "analysis_records" / f"{safe_timestamp}.json"

    def _process_snapshot(
        self,
        event_id: str,
        snapshot: dict[str, Any],
        entry: dict[str, Any],
        cursor_timestamp: str,
    ) -> None:
        with self._event_lock(event_id):
            self._process_snapshot_locked(
                event_id,
                snapshot,
                entry,
                cursor_timestamp,
            )

    def _process_snapshot_locked(
        self,
        event_id: str,
        snapshot: dict[str, Any],
        entry: dict[str, Any],
        cursor_timestamp: str,
    ) -> None:
        meta = load_meta(event_id)
        if str(meta.get("analysis_status") or "").startswith("finished"):
            self._mark_snapshots_superseded(
                event_id,
                [{"timestamp": cursor_timestamp, "file": ""}],
                reason="Settlement confirmado antes del análisis del snapshot.",
                status=str(meta.get("analysis_status")),
            )
            return
        if (
            meta.get("last_processed_snapshot_at")
            and str(cursor_timestamp)
            <= str(meta["last_processed_snapshot_at"])
        ):
            return
        if not meta.get("analysis_match_date"):
            player1, player2, tournament, match_date = self._match_details(
                snapshot,
                entry,
                meta,
            )
            identity = self._resolve_tournament_identity(snapshot, entry, meta)
            meta.update(
                {
                    "analysis_player1": player1,
                    "analysis_player2": player2,
                    "analysis_tournament": identity.display_name,
                    "analysis_tournament_surface": identity.surface,
                    "analysis_match_date": match_date,
                }
            )
            self._save_analysis_meta(event_id, meta)
        else:
            identity = self._resolve_tournament_identity(snapshot, entry, meta)
            drift = self._tournament_identity_drift(meta, identity)
            sync_changed = self._sync_analysis_tournament(meta, identity)
            if meta.get("analysts_completed") and (drift or sync_changed):
                meta["analysts_completed"] = False
                meta.pop("analyst_report_errors", None)
                self._save_analysis_meta(event_id, meta)
            elif sync_changed:
                self._save_analysis_meta(event_id, meta)
        reports = self._load_reports(event_id)
        existing_report_errors = self._report_quality_errors(reports)
        if meta.get("analysts_completed") and existing_report_errors:
            meta["analysts_completed"] = False
            meta["analyst_report_errors"] = existing_report_errors
            self._save_analysis_meta(event_id, meta)
        graph = self._get_graph()

        if not meta.get("analysts_completed"):
            meta["analysis_status"] = "analysts_running"
            meta["analysis_started_at"] = meta.get("analysis_started_at") or _utc_now_iso()
            self._save_analysis_meta(event_id, meta)
            max_runtime = max(
                60,
                int(self.config.get("analysts_max_runtime_sec", 600)),
            )
            max_attempts = max(
                1,
                int(self.config.get("analysts_in_process_retries", 3)),
            )
            retry_sleep = max(
                1,
                int(self.config.get("analysts_retry_sleep_sec", 5)),
            )
            started_monotonic = time.monotonic()
            missing_reports: list[str] = []
            analyst_errors: dict[str, Any] = {}
            report_errors: dict[str, str] = {}
            reports = self._load_reports(event_id)
            for attempt in range(1, max_attempts + 1):
                initial_state = self._build_state(
                    event_id, snapshot, entry, meta, reports
                )
                tool_log_offset = self._tool_log_offset()
                analyst_result = graph.run_analysts_once(initial_state)
                reports = self._save_reports(event_id, analyst_result)
                report_errors = self._report_quality_errors(reports)
                missing_reports = list(report_errors)
                analyst_errors = analyst_result.get("analyst_errors") or {}
                infrastructure_errors = self._tool_infrastructure_errors_since(
                    tool_log_offset
                )
                if infrastructure_errors:
                    analyst_errors["tool_infrastructure"] = " | ".join(
                        infrastructure_errors
                    )
                meta["analyst_errors"] = analyst_errors
                meta["analyst_report_errors"] = report_errors
                meta["analysts_completed_count"] = (
                    len(REPORT_KEYS) - len(missing_reports)
                )
                meta["analysts_expected_count"] = len(REPORT_KEYS)
                meta["analysts_attempt"] = attempt
                self._save_analysis_meta(event_id, meta)
                if not missing_reports:
                    break
                elapsed = time.monotonic() - started_monotonic
                if attempt >= max_attempts or elapsed >= max_runtime:
                    break
                sleep_for = min(retry_sleep * (2 ** (attempt - 1)), 60)
                log.warning(
                    "Analistas incompletos event_id=%s intento=%s/%s "
                    "faltan=%s; reintento en %ss",
                    event_id,
                    attempt,
                    max_attempts,
                    ",".join(missing_reports),
                    sleep_for,
                )
                time.sleep(sleep_for)
            if missing_reports:
                meta["analysts_completed"] = False
                meta["analysis_status"] = "error"
                meta["analysis_error"] = (
                    "Informes de analistas ausentes o no válidos: "
                    + ", ".join(missing_reports)
                    + (
                        f". Errores: {json.dumps(analyst_errors, ensure_ascii=False)}"
                        if analyst_errors
                        else ""
                    )
                )
                self._save_analysis_meta(event_id, meta)
                raise AnalysisDeferredError(meta["analysis_error"])
            meta["analysts_completed"] = True
            meta.pop("analyst_report_errors", None)
            meta["analysts_completed_at"] = _utc_now_iso()
            meta["analysis_status"] = "generalist_running"
            self._save_analysis_meta(event_id, meta)

        state = self._build_state(event_id, snapshot, entry, meta, reports)
        meta["analysis_status"] = "generalist_running"
        meta["analysis_current_snapshot_at"] = snapshot.get("timestamp")
        meta["analysis_current_started_at"] = _utc_now_iso()
        self._save_analysis_meta(event_id, meta)

        journal_path = self._journal_path(event_id, cursor_timestamp)
        if journal_path.exists():
            try:
                record = json.loads(journal_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise AnalysisDeferredError(
                    f"Journal de análisis inválido: {exc}"
                ) from exc
        else:
            result = graph.run_generalist_timestep(state)
            if result.get("technical_fallback"):
                raise AnalysisDeferredError(
                    result.get("generalist_error")
                    or "El generalista devolvió un fallback técnico."
                )
            record = result.get("generalist_record")
            if not isinstance(record, dict):
                raise AnalysisDeferredError(
                    "El generalista no devolvió un registro estructurado."
                )
            _, record = self._prepare_commit(
                event_id,
                cursor_timestamp,
                snapshot,
                meta,
                record,
            )
            _atomic_write_text(
                journal_path,
                json.dumps(record, ensure_ascii=False, indent=2),
            )

        committed_meta, record = self._prepare_commit(
            event_id,
            cursor_timestamp,
            snapshot,
            meta,
            record,
        )
        decision = format_decision_display(record)
        _save_turn_log(record, str(match_dir(event_id) / "generalist_turns.jsonl"))
        _write_context_file(
            str(self._context_path(event_id)),
            record=record,
            scraper_snapshot=snapshot,
        )
        decision_path = match_dir(event_id) / "decision.md"
        _atomic_write_text(decision_path, str(decision))

        committed_meta["last_analysis_step"] = int(record.get("step_index", state["step_index"]))
        committed_meta["last_analysis_at"] = _utc_now_iso()
        committed_meta["last_processed_snapshot_at"] = cursor_timestamp
        committed_meta["last_decision"] = decision
        target = (record.get("target") or {}).get("tool_call") or {}
        if target.get("policy_rejected"):
            # Un rechazo de política es una decisión segura (Wait), no un fallo técnico.
            committed_meta["analysis_status"] = "running"
            committed_meta["last_policy_rejection_reason"] = (
                (target.get("arguments") or {}).get("reason")
            )
            committed_meta.pop("analysis_degraded_reason", None)
        else:
            committed_meta["analysis_status"] = "running"
            committed_meta.pop("analysis_degraded_reason", None)
            committed_meta.pop("last_policy_rejection_reason", None)
        for key in (
            "analysis_current_snapshot_at",
            "analysis_current_started_at",
            "analysis_error",
            "analysis_error_at",
            "analysis_failure_snapshot_at",
            "analysis_failure_count",
            "analysis_next_retry_at",
        ):
            committed_meta.pop(key, None)
        self._save_analysis_meta(
            event_id,
            committed_meta,
            remove_keys=(
                "analysis_current_snapshot_at",
                "analysis_current_started_at",
                "analysis_error",
                "analysis_error_at",
                "analysis_failure_snapshot_at",
                "analysis_failure_count",
                "analysis_next_retry_at",
            ),
        )
        log.info(
            "Análisis automático completado event_id=%s timestep=%s",
            event_id,
            state["step_index"],
        )
