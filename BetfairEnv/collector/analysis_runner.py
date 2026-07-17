"""Orquestación automática de analistas y generalista por partido."""

from __future__ import annotations

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from collector.paths import ROOT
from collector.storage import (
    _atomic_write_text,
    list_snapshot_files,
    load_meta,
    load_snapshot,
    match_dir,
    save_meta,
)
from tennisAgents.default_config import DEFAULT_CONFIG
from tennisAgents.graph.trading_graph import TennisAgentsGraph
from tennisAgents.utils.enumerations import REPORTS, STATE

log = logging.getLogger("collector.analysis")

REPORT_KEYS = (
    REPORTS.news_report,
    REPORTS.players_report,
    REPORTS.tournament_report,
    REPORTS.weather_report,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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
        self._graph: TennisAgentsGraph | None = None
        self._graph_lock = threading.Lock()

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

    def _get_graph(self) -> TennisAgentsGraph:
        if self._graph is None:
            with self._graph_lock:
                if self._graph is None:
                    self._graph = TennisAgentsGraph(
                        selected_analysts=["news", "players", "tournament", "weather"],
                        config=self.config,
                        debug=False,
                    )
        return self._graph

    def submit_snapshot(
        self,
        event_id: str,
        snapshot: dict[str, Any],
        entry: dict[str, Any],
    ) -> None:
        """Señala que hay snapshots pendientes para este partido."""
        event_key = str(event_id)
        with self._lock:
            self._pending[event_key] = dict(entry)
            if event_key in self._processing:
                return
            self._processing.add(event_key)
        self._executor.submit(self._drain_event, event_key)

    def shutdown(self) -> None:
        """Completa la tarea activa y evita perder su estado al apagar."""
        self._executor.shutdown(wait=True, cancel_futures=True)

    def _drain_event(self, event_id: str) -> None:
        try:
            while True:
                with self._lock:
                    entry = self._pending.get(event_id)
                if entry is None:
                    break

                meta = load_meta(event_id)
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

                snapshot_info = pending[0]
                snapshot_timestamp = snapshot_info["timestamp"]
                try:
                    snapshot = load_snapshot(event_id, snapshot_info["file"])
                    success = False
                    error: Exception | None = None
                    for attempt in range(3):
                        try:
                            self._process_snapshot(event_id, snapshot, entry)
                            success = True
                            break
                        except Exception as exc:
                            error = exc
                            if attempt < 2:
                                time.sleep(2 ** attempt)
                    if not success and error is not None:
                        raise error
                except Exception as exc:
                    meta = load_meta(event_id)
                    meta["analysis_status"] = "error"
                    meta["analysis_error"] = str(exc)
                    meta["analysis_error_at"] = _utc_now_iso()
                    meta["last_processed_snapshot_at"] = snapshot_timestamp
                    meta.pop("analysis_current_snapshot_at", None)
                    meta.pop("analysis_current_started_at", None)
                    save_meta(event_id, meta)
                    log.exception("Error analizando event_id=%s", event_id)
                else:
                    meta = load_meta(event_id)
                    meta["last_processed_snapshot_at"] = snapshot_timestamp
                    meta.pop("analysis_error", None)
                    meta.pop("analysis_error_at", None)
                    save_meta(event_id, meta)
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
            text = str(content)
            _atomic_write_text(reports_dir / f"{key}.md", text)
            reports[key] = text
        return reports

    def _match_details(
        self,
        snapshot: dict[str, Any],
        entry: dict[str, Any],
    ) -> tuple[str, str, str, str]:
        betfair = snapshot.get("betfair") or {}
        flashscore = snapshot.get("flashscore") or {}
        flashscore_match = flashscore.get("match") or {}
        player1 = entry.get("player1") or betfair.get("player1") or flashscore.get("player1") or ""
        player2 = entry.get("player2") or betfair.get("player2") or flashscore.get("player2") or ""
        tournament = (
            entry.get("competition")
            or betfair.get("competition")
            or flashscore_match.get("tournament")
            or "Tennis"
        )
        timestamp = str(snapshot.get("timestamp") or _utc_now_iso())
        match_date = timestamp[:10]
        return str(player1), str(player2), str(tournament), match_date

    def _build_state(
        self,
        event_id: str,
        snapshot: dict[str, Any],
        entry: dict[str, Any],
        meta: dict[str, Any],
        reports: dict[str, str],
    ) -> dict[str, Any]:
        player1, player2, tournament, match_date = self._match_details(snapshot, entry)
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

    @staticmethod
    def _extract_tool_call(result: dict[str, Any]) -> dict[str, Any] | None:
        messages = result.get(STATE.messages) or []
        if not messages:
            return None
        calls = getattr(messages[-1], "tool_calls", None) or []
        if not calls:
            return None
        call = calls[0]
        if isinstance(call, dict):
            return call
        return {
            "name": getattr(call, "name", ""),
            "args": getattr(call, "args", {}) or {},
            "id": getattr(call, "id", None),
        }

    def _persist_action(self, meta: dict[str, Any], result: dict[str, Any]) -> None:
        call = self._extract_tool_call(result)
        if not call:
            return
        args = call.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        name = str(call.get("name") or "Wait").lower()
        action = {
            "timestamp": _utc_now_iso(),
            "tool": name,
            "args": args,
        }
        previous = [
            previous_action
            for previous_action in (meta.get("previous_actions") or [])
            if isinstance(previous_action, dict)
        ]
        previous.append(action)
        meta["previous_actions"] = previous[-50:]

        positions = [
            position
            for position in (meta.get("open_positions") or [])
            if isinstance(position, dict)
        ]
        match_id = args.get("match_id", "")
        if name == "bet":
            stake = max(0.0, _safe_float(args.get("stake"), 0.0))
            positions.append(
                {
                    "position_id": match_id,
                    "selection": args.get("selection", ""),
                    "market": args.get("market", ""),
                    "stake": stake,
                    "opened_at": action["timestamp"],
                }
            )
            meta["available_balance"] = max(
                0.0,
                _safe_float(
                    meta.get(
                        "available_balance",
                        meta.get("wallet_balance", self.config.get("automated_wallet_balance", 100.0)),
                    ),
                    _safe_float(self.config.get("automated_wallet_balance"), 100.0),
                )
                - stake,
            )
        elif name == "close":
            position_id = args.get("position_id") or match_id
            positions = [p for p in positions if p.get("position_id") != position_id]
        meta["open_positions"] = positions
        meta["last_action"] = action

    def _process_snapshot(
        self,
        event_id: str,
        snapshot: dict[str, Any],
        entry: dict[str, Any],
    ) -> None:
        meta = load_meta(event_id)
        reports = self._load_reports(event_id)
        graph = self._get_graph()

        if not meta.get("analysts_completed"):
            meta["analysis_status"] = "analysts_running"
            meta["analysis_started_at"] = _utc_now_iso()
            save_meta(event_id, meta)
            initial_state = self._build_state(event_id, snapshot, entry, meta, reports)
            analyst_result = graph.run_analysts_once(initial_state)
            reports = self._save_reports(event_id, analyst_result)
            meta["analysts_completed"] = True
            meta["analysts_completed_at"] = _utc_now_iso()
            meta["analysis_status"] = "generalist_running"
            save_meta(event_id, meta)

        state = self._build_state(event_id, snapshot, entry, meta, reports)
        meta["analysis_status"] = "generalist_running"
        meta["analysis_current_snapshot_at"] = snapshot.get("timestamp")
        meta["analysis_current_started_at"] = _utc_now_iso()
        save_meta(event_id, meta)
        result = graph.run_generalist_timestep(state)
        decision = result.get(STATE.final_bet_decision) or ""
        self._persist_action(meta, result)
        meta["last_analysis_step"] = state["step_index"]
        meta["last_analysis_at"] = _utc_now_iso()
        meta["analysis_status"] = "running"
        meta["last_decision"] = decision
        meta.pop("analysis_current_snapshot_at", None)
        meta.pop("analysis_current_started_at", None)
        save_meta(event_id, meta)

        decision_path = match_dir(event_id) / "decision.md"
        _atomic_write_text(decision_path, str(decision))
        log.info(
            "Análisis automático completado event_id=%s timestep=%s",
            event_id,
            state["step_index"],
        )
