"""Control del proceso colector (arrancar / detener / estado)."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

from collector.anti_block import cycle_interval
from collector.config import INTERVAL_BASE_SEC, INTERVAL_JITTER_SEC
from collector.paths import ROOT, RUN_DIR
from collector.shutdown_utils import void_open_positions_on_shutdown
from collector.storage import _atomic_write_text, clear_dataset, load_index

PID_FILE = RUN_DIR / "collector.pid"
LOG_FILE = RUN_DIR / "collector.log"
LAST_CYCLE_FILE = RUN_DIR / "collector.last_cycle"
STOP_FILE = RUN_DIR / "collector.stop"
CONTROL_LOCK_FILE = RUN_DIR / "collector.control.lock"
RUNNER = ROOT / "collector" / "runner.py"

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
_PROCESS_CONTROL_LOCK = threading.RLock()


@contextmanager
def _interprocess_control_lock():
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    with CONTROL_LOCK_FILE.open("a+b") as lock_file:
        if lock_file.tell() == 0:
            lock_file.write(b"\0")
            lock_file.flush()
        lock_file.seek(0)
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _synchronized(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        with _PROCESS_CONTROL_LOCK:
            with _interprocess_control_lock():
                return func(*args, **kwargs)

    return wrapped


def _read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        raw = PID_FILE.read_text(encoding="utf-8").strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return int(raw)
        if isinstance(payload, dict):
            return int(payload.get("pid"))
        return int(payload)
    except (TypeError, ValueError):
        return None


def _pid_alive(pid: int) -> bool:
    if not _pid_exists(pid):
        return False
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    (
                        f"$p=Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\" "
                        "-ErrorAction SilentlyContinue; if($p){$p.CommandLine}"
                    ),
                ],
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        command_line = result.stdout.strip().lower().replace("/", "\\")
        return bool(
            command_line
            and "collector\\runner.py" in command_line
        )
    proc_cmdline = Path(f"/proc/{pid}/cmdline")
    if proc_cmdline.exists():
        try:
            command_line = proc_cmdline.read_bytes().decode(
                "utf-8",
                errors="replace",
            )
            return "collector/runner.py" in command_line.replace("\\", "/")
        except OSError:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _pid_exists(pid: int) -> bool:
    if sys.platform == "win32":
        import ctypes

        process = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not process:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if not ctypes.windll.kernel32.GetExitCodeProcess(
                process,
                ctypes.byref(exit_code),
            ):
                return False
            return exit_code.value == 259
        finally:
            ctypes.windll.kernel32.CloseHandle(process)
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
        "cycle_state": None,
        "cycle_started_at": None,
        "heartbeat_at": None,
        "cycle_duration_sec": None,
        "cycle_snapshots": None,
        "cycle_errors": None,
        "cycle_message": None,
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
    health = {
        "cycle_state": raw.get("cycle_state"),
        "cycle_started_at": raw.get("cycle_started_at"),
        "heartbeat_at": raw.get("heartbeat_at"),
        "cycle_duration_sec": raw.get("cycle_duration_sec"),
        "cycle_snapshots": raw.get("snapshots"),
        "cycle_errors": raw.get("errors"),
        "cycle_message": raw.get("message"),
    }
    if not last_s:
        return {**empty, **health}

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
        **health,
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


@_synchronized
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
    STOP_FILE.unlink(missing_ok=True)
    proc = subprocess.Popen(
        [sys.executable, str(RUNNER)],
        cwd=str(ROOT),
        # runner.py gestiona el archivo rotativo; mantener otro descriptor
        # abierto aquí impediría rotarlo correctamente en Windows.
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        creationflags=(
            CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
            if sys.platform == "win32"
            else 0
        ),
    )
    _atomic_write_text(
        PID_FILE,
        json.dumps(
            {
                "pid": proc.pid,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "runner": str(RUNNER),
            }
        ),
    )
    return {
        **collector_status(),
        "message": "Colector iniciado",
        "already_running": False,
    }


@_synchronized
def stop_collector() -> dict:
    _cleanup_stale_pid()
    pid = _read_pid()
    if pid is None or not _pid_alive(pid):
        PID_FILE.unlink(missing_ok=True)
        STOP_FILE.unlink(missing_ok=True)
        return {
            **collector_status(),
            "message": "El colector no estaba en ejecución",
            "was_running": False,
        }

    graceful = False
    _atomic_write_text(STOP_FILE, datetime.now(timezone.utc).isoformat())
    if sys.platform == "win32":
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if not _pid_exists(pid):
                graceful = True
                break
            time.sleep(0.5)
        if not graceful and _pid_exists(pid):
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
            )
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass

    void_open_positions_on_shutdown()

    PID_FILE.unlink(missing_ok=True)
    if graceful:
        STOP_FILE.unlink(missing_ok=True)
    return {
        **collector_status(),
        "message": "Colector detenido",
        "was_running": True,
        "stopped_pid": pid,
        "graceful": graceful,
    }


@_synchronized
def clear_collector_data() -> dict:
    """Detiene el colector si hace falta y borra todo el dataset recolectado."""
    was_running = False
    status = collector_status()
    if status.get("running"):
        stop_collector.__wrapped__()
        was_running = True

    cleared = clear_dataset()
    return {
        **collector_status(),
        **cleared,
        "collector_was_running": was_running,
    }
