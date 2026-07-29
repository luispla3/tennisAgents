"""Bucle del colector BetfairEnv."""

from __future__ import annotations

import json
import logging
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collector.anti_block import cycle_interval
from collector.config import (
    CAPTURE_GAP_WARN_SEC,
    DEFAULT_SPORT,
    NO_SNAPSHOT_ALERT_SEC,
)
from collector.control_signals import watch_stop_file
from collector.paths import RUN_DIR, ensure_scraper_paths

ensure_scraper_paths()
from collector.snapshot import collect_once
from collector.storage import (
    _atomic_write_text,
    effective_is_live,
    load_index,
    seconds_until_earliest_due,
)

LAST_CYCLE_FILE = RUN_DIR / "collector.last_cycle"
LOG_FILE = RUN_DIR / "collector.log"
STOP_FILE = RUN_DIR / "collector.stop"


def setup_logging() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            RotatingFileHandler(
                LOG_FILE,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            ),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _detect_capture_gap(log: logging.Logger) -> float | None:
    """Devuelve el hueco en segundos si supera el umbral de aviso."""
    if not LAST_CYCLE_FILE.exists():
        return None
    try:
        previous = json.loads(LAST_CYCLE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    last_at = _parse_iso(previous.get("last_cycle_at"))
    if last_at is None:
        return None
    gap_sec = (datetime.now(timezone.utc) - last_at).total_seconds()
    if gap_sec <= CAPTURE_GAP_WARN_SEC:
        return None
    log.warning(
        "Gap de captura detectado: %.0fs desde el último ciclo completado "
        "(umbral=%ss). Posible sleep/crash; se reconciliará al reanudar.",
        gap_sec,
        CAPTURE_GAP_WARN_SEC,
    )
    return round(gap_sec, 1)


def _alert_stale_snapshots(log: logging.Logger, previous: dict) -> None:
    """Alerta si hay partidos activos y no llegan snapshots nuevos."""
    last_success = _parse_iso(previous.get("last_snapshot_success_at"))
    if last_success is None:
        return
    quiet_sec = (datetime.now(timezone.utc) - last_success).total_seconds()
    if quiet_sec <= NO_SNAPSHOT_ALERT_SEC:
        return
    try:
        matches = load_index().get("matches") or {}
    except Exception:
        return
    live_count = sum(
        1
        for entry in matches.values()
        if isinstance(entry, dict) and effective_is_live(entry)
    )
    if live_count <= 0:
        return
    log.warning(
        "Alerta: sin snapshots nuevos en %.0fs con %s partido(s) activo(s) "
        "(umbral=%ss).",
        quiet_sec,
        live_count,
        NO_SNAPSHOT_ALERT_SEC,
    )


class CycleHeartbeat:
    """Mantiene una señal de vida incluso durante ciclos largos."""

    def __init__(self) -> None:
        self.started_at = _utc_now_iso()
        self.started_monotonic = time.monotonic()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _payload(self) -> dict:
        previous = {}
        if LAST_CYCLE_FILE.exists():
            try:
                previous = json.loads(LAST_CYCLE_FILE.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                previous = {}
        return {
            **previous,
            "cycle_state": "running",
            "cycle_started_at": self.started_at,
            "heartbeat_at": _utc_now_iso(),
        }

    def start(self) -> None:
        _atomic_write_text(LAST_CYCLE_FILE, json.dumps(self._payload()))
        self.thread.start()

    def _run(self) -> None:
        while not self.stop_event.wait(30):
            _atomic_write_text(LAST_CYCLE_FILE, json.dumps(self._payload()))

    def finish(self, summary: dict, *, state: str) -> None:
        self.stop_event.set()
        self.thread.join(timeout=2)
        now = _utc_now_iso()
        previous = {}
        if LAST_CYCLE_FILE.exists():
            try:
                previous = json.loads(LAST_CYCLE_FILE.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                previous = {}
        snaps = int(summary.get("snapshots", 0) or 0)
        last_snapshot_success_at = previous.get("last_snapshot_success_at")
        if snaps > 0:
            last_snapshot_success_at = now
        payload = {
            "last_cycle_at": now,
            "heartbeat_at": now,
            "cycle_started_at": self.started_at,
            "cycle_duration_sec": round(
                time.monotonic() - self.started_monotonic,
                3,
            ),
            "cycle_state": state,
            "last_snapshot_success_at": last_snapshot_success_at,
            **summary,
        }
        _atomic_write_text(LAST_CYCLE_FILE, json.dumps(payload, ensure_ascii=False))


def main() -> int:
    setup_logging()
    log = logging.getLogger("collector.runner")
    sport = DEFAULT_SPORT
    try:
        from collector.analysis_runner import AutomatedAnalysisRunner

        analysis_runner = AutomatedAnalysisRunner()
        migrated_ledgers = analysis_runner.migrate_legacy_ledgers()
        if migrated_ledgers:
            log.warning(
                "Ledgers legacy migrados a esquema v2: %s",
                migrated_ledgers,
            )
        quarantined = analysis_runner.sanitize_training_labels()
        if quarantined:
            log.warning(
                "Turnos legacy puestos en cuarentena: %s",
                quarantined,
            )
        healed = analysis_runner.reconcile_session_on_startup()
        if any(healed.values()):
            log.info(
                "Autocuración de sesión: index_synced=%s stuck_reset=%s "
                "analysts_invalidated=%s positions_voided=%s events_healed=%s",
                healed.get("index_synced", 0),
                healed.get("stuck_status_reset", 0),
                healed.get("analysts_invalidated", 0),
                healed.get("positions_voided", 0),
                healed.get("events_healed", 0),
            )
        resumed = analysis_runner.resume_pending()
        if resumed:
            log.info("Análisis pendientes reanudados: %s partido(s)", resumed)
    except Exception:
        analysis_runner = None
        log.exception(
            "No se pudo inicializar la automatización de analistas; "
            "el colector continuará capturando snapshots."
        )
    log.info("Colector iniciado (deporte=%s)", sport)
    stop_event = threading.Event()
    STOP_FILE.unlink(missing_ok=True)

    def request_stop(*_args) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, request_stop)

    stop_watcher = threading.Thread(
        target=watch_stop_file,
        args=(stop_event, STOP_FILE),
        daemon=True,
    )
    stop_watcher.start()

    try:
        while not stop_event.is_set():
            ensure_scraper_paths()
            capture_gap_sec = _detect_capture_gap(log)
            previous_cycle: dict = {}
            if LAST_CYCLE_FILE.exists():
                try:
                    previous_cycle = json.loads(
                        LAST_CYCLE_FILE.read_text(encoding="utf-8")
                    )
                except (OSError, json.JSONDecodeError):
                    previous_cycle = {}
            _alert_stale_snapshots(log, previous_cycle)
            heartbeat = CycleHeartbeat()
            heartbeat.start()
            try:
                summary = collect_once(
                    sport=sport,
                    snapshot_callback=(
                        analysis_runner.submit_snapshot
                        if analysis_runner is not None
                        else None
                    ),
                )
                if capture_gap_sec is not None:
                    summary["capture_gap_sec"] = capture_gap_sec
                if analysis_runner is not None:
                    reconciled = analysis_runner.reconcile_finished_matches()
                    if reconciled:
                        log.info(
                            "Partidos finalizados reconciliados: %s",
                            reconciled,
                        )
                errors = int(summary.get("errors", 0) or 0)
                snaps = int(summary.get("snapshots", 0) or 0)
                cycle_state = "ok" if errors == 0 else "degraded"
                heartbeat.finish(summary, state=cycle_state)
                if cycle_state == "ok":
                    log.info("Ciclo OK — snapshots=%s errores=%s", snaps, errors)
                else:
                    log.warning(
                        "Ciclo degradado — snapshots=%s errores=%s mensaje=%s",
                        snaps,
                        errors,
                        summary.get("message") or "",
                    )

                wait = seconds_until_earliest_due()
                if wait is not None and wait <= 0:
                    log.info("Snapshot(s) vencido(s) — ciclo inmediato")
                    continue

                interval = cycle_interval() if wait is None else min(wait, cycle_interval())
                log.info("Próximo ciclo en %.0f s", interval)
                stop_event.wait(interval)
            except Exception as exc:
                heartbeat.finish(
                    {
                        "snapshots": 0,
                        "errors": 1,
                        "message": f"{type(exc).__name__}: {exc}",
                        **(
                            {"capture_gap_sec": capture_gap_sec}
                            if capture_gap_sec is not None
                            else {}
                        ),
                    },
                    state="failed",
                )
                log.exception("Error en ciclo del colector")
                stop_event.wait(30)
    except KeyboardInterrupt:
        request_stop()
    finally:
        log.info("Colector detenido")
        if analysis_runner is not None:
            analysis_runner.shutdown()
        STOP_FILE.unlink(missing_ok=True)
        stop_watcher.join(timeout=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
