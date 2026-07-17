"""Control del proceso colector (arrancar / detener / estado)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from collector.anti_block import cycle_interval
from collector.config import INTERVAL_BASE_SEC, INTERVAL_JITTER_SEC
from collector.paths import ROOT, RUN_DIR
from collector.storage import _atomic_write_text, clear_dataset, load_index

PID_FILE = RUN_DIR / "collector.pid"
LOG_FILE = RUN_DIR / "collector.log"
LAST_CYCLE_FILE = RUN_DIR / "collector.last_cycle"
RUNNER = ROOT / "collector" / "runner.py"

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW,
        )
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _cleanup_stale_pid() -> None:
    pid = _read_pid()
    if pid is not None and not _pid_alive(pid):
        PID_FILE.unlink(missing_ok=True)


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _cycle_timing() -> dict:
    low = max(60.0, INTERVAL_BASE_SEC - INTERVAL_JITTER_SEC)
    high = INTERVAL_BASE_SEC + INTERVAL_JITTER_SEC
    empty = {
        "last_cycle_at": None,
        "next_cycle_at": None,
        "seconds_until_next": None,
        "progress": None,
        "interval_sec_min": low,
        "interval_sec_max": high,
    }
    if not LAST_CYCLE_FILE.exists():
        return empty
    try:
        raw = json.loads(LAST_CYCLE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return empty

    last_s = raw.get("last_cycle_at")
    next_s = raw.get("next_cycle_at")
    interval = raw.get("interval_sec")
    if not last_s:
        return empty

    now = datetime.now(timezone.utc)
    try:
        last_dt = _parse_iso(last_s)
    except (TypeError, ValueError):
        return empty
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)

    try:
        next_dt = _parse_iso(next_s) if next_s else None
    except (TypeError, ValueError):
        next_dt = None
    if next_dt and next_dt.tzinfo is None:
        next_dt = next_dt.replace(tzinfo=timezone.utc)
    try:
        interval_value = float(interval) if interval is not None else float(INTERVAL_BASE_SEC)
    except (TypeError, ValueError):
        interval_value = float(INTERVAL_BASE_SEC)
    interval_value = min(float(high), max(float(low), interval_value))
    if next_dt is None:
        next_dt = last_dt + timedelta(seconds=interval_value)

    if next_dt <= now:
        next_dt = now + timedelta(seconds=interval_value)
        remaining = interval_value
        progress = 0.0
    else:
        total = (next_dt - last_dt).total_seconds() or interval_value
        elapsed = (now - last_dt).total_seconds()
        remaining = max(0.0, (next_dt - now).total_seconds())
        progress = min(1.0, max(0.0, elapsed / total)) if total > 0 else 0.0

    return {
        "last_cycle_at": last_dt.isoformat(),
        "next_cycle_at": next_dt.isoformat(),
        "seconds_until_next": remaining,
        "progress": progress,
        "interval_sec": interval_value,
        "interval_sec_min": low,
        "interval_sec_max": high,
    }


def collector_status() -> dict:
    _cleanup_stale_pid()
    pid = _read_pid()
    running = pid is not None and _pid_alive(pid)
    status = {
        "running": running,
        "pid": pid if running else None,
        "interval_hint": "~2 min (90–150 s con jitter)",
        "log_file": str(LOG_FILE.relative_to(ROOT)).replace("\\", "/"),
    }
    status.update(_cycle_timing())
    return status


def start_collector() -> dict:
    _cleanup_stale_pid()
    pid = _read_pid()
    if pid is not None and _pid_alive(pid):
        return {
            **collector_status(),
            "message": "El colector ya está en ejecución",
            "already_running": True,
        }

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [sys.executable, str(RUNNER)],
        cwd=str(ROOT),
        # runner.py gestiona el archivo rotativo; mantener otro descriptor
        # abierto aquí impediría rotarlo correctamente en Windows.
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        creationflags=CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    _atomic_write_text(PID_FILE, str(proc.pid))
    return {
        **collector_status(),
        "message": "Colector iniciado",
        "already_running": False,
    }


def stop_collector() -> dict:
    _cleanup_stale_pid()
    pid = _read_pid()
    if pid is None or not _pid_alive(pid):
        PID_FILE.unlink(missing_ok=True)
        return {
            **collector_status(),
            "message": "El colector no estaba en ejecución",
            "was_running": False,
        }

    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
        )
    else:
        try:
            os.kill(pid, 15)
        except OSError:
            pass

    PID_FILE.unlink(missing_ok=True)
    return {
        **collector_status(),
        "message": "Colector detenido",
        "was_running": True,
        "stopped_pid": pid,
    }


def clear_collector_data() -> dict:
    """Detiene el colector si hace falta y borra todo el dataset recolectado."""
    was_running = False
    status = collector_status()
    if status.get("running"):
        stop_collector()
        was_running = True

    cleared = clear_dataset()
    return {
        **collector_status(),
        **cleared,
        "collector_was_running": was_running,
    }
