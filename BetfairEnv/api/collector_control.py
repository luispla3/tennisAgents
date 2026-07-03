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
from collector.storage import load_index

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
    except json.JSONDecodeError:
        return empty

    last_s = raw.get("last_cycle_at")
    next_s = raw.get("next_cycle_at")
    interval = raw.get("interval_sec")
    if not last_s:
        return empty

    now = datetime.now(timezone.utc)
    last_dt = _parse_iso(last_s)
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)

    next_dt = _parse_iso(next_s) if next_s else None
    if next_dt and next_dt.tzinfo is None:
        next_dt = next_dt.replace(tzinfo=timezone.utc)
    if next_dt is None and interval is not None:
        next_dt = last_dt + timedelta(seconds=float(interval))
    if next_dt is None:
        return {**empty, "last_cycle_at": last_dt.isoformat()}

    if next_dt <= now:
        resolved = float(interval) if interval is not None else float(INTERVAL_BASE_SEC)
        next_dt = now + timedelta(seconds=resolved)
        remaining = resolved
        progress = 0.0
    else:
        total = (next_dt - last_dt).total_seconds() or resolved if (resolved := (float(interval) if interval else float(INTERVAL_BASE_SEC))) else 1.0
        elapsed = (now - last_dt).total_seconds()
        remaining = max(0.0, (next_dt - now).total_seconds())
        progress = min(1.0, max(0.0, elapsed / total)) if total > 0 else 0.0

    return {
        "last_cycle_at": last_dt.isoformat(),
        "next_cycle_at": next_dt.isoformat(),
        "seconds_until_next": remaining,
        "progress": progress,
        "interval_sec": interval,
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
    log_handle = open(LOG_FILE, "a", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, str(RUNNER)],
        cwd=str(ROOT),
        stdout=log_handle,
        stderr=log_handle,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        creationflags=CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
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
