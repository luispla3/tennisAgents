"""Bucle del colector BetfairEnv."""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collector.anti_block import cycle_interval
from collector.config import DEFAULT_SPORT
from collector.paths import RUN_DIR
from collector.snapshot import collect_once
from collector.storage import _atomic_write_text, seconds_until_earliest_due

LAST_CYCLE_FILE = RUN_DIR / "collector.last_cycle"
LOG_FILE = RUN_DIR / "collector.log"


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


def write_last_cycle() -> None:
    payload = {"last_cycle_at": datetime.now(timezone.utc).isoformat()}
    _atomic_write_text(LAST_CYCLE_FILE, json.dumps(payload))


def main() -> int:
    setup_logging()
    log = logging.getLogger("collector.runner")
    sport = DEFAULT_SPORT
    try:
        from collector.analysis_runner import AutomatedAnalysisRunner

        analysis_runner = AutomatedAnalysisRunner()
    except Exception:
        analysis_runner = None
        log.exception(
            "No se pudo inicializar la automatización de analistas; "
            "el colector continuará capturando snapshots."
        )
    log.info("Colector iniciado (deporte=%s)", sport)

    while True:
        try:
            summary = collect_once(
                sport=sport,
                snapshot_callback=(
                    analysis_runner.submit_snapshot
                    if analysis_runner is not None
                    else None
                ),
            )
            errors = summary.get("errors", 0)
            snaps = summary.get("snapshots", 0)
            log.info("Ciclo OK — snapshots=%s errores=%s", snaps, errors)
            write_last_cycle()

            wait = seconds_until_earliest_due()
            if wait is not None and wait <= 0:
                log.info("Snapshot(s) vencido(s) — ciclo inmediato")
                continue

            interval = cycle_interval() if wait is None else min(wait, cycle_interval())
            log.info("Próximo ciclo en %.0f s", interval)
            time.sleep(interval)
        except KeyboardInterrupt:
            log.info("Colector detenido")
            if analysis_runner is not None:
                analysis_runner.shutdown()
            return 0
        except Exception:
            log.exception("Error en ciclo del colector")
            time.sleep(30)


if __name__ == "__main__":
    raise SystemExit(main())
