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
from collector.config import DEFAULT_SPORT
from collector.control_signals import watch_stop_file
from collector.paths import RUN_DIR
from collector.snapshot import collect_once
from collector.storage import _atomic_write_text, seconds_until_earliest_due

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
        payload = {
            "last_cycle_at": now,
            "heartbeat_at": now,
            "cycle_started_at": self.started_at,
            "cycle_duration_sec": round(
                time.monotonic() - self.started_monotonic,
                3,
            ),
            "cycle_state": state,
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
