"""Supervisor persistente de la API y el colector BetfairEnv."""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
RUN_DIR = ROOT / ".run"
LOG_FILE = RUN_DIR / "supervisor.log"
API_LOG_FILE = RUN_DIR / "api.log"
PID_FILE = RUN_DIR / "supervisor.pid"
LOCK_FILE = RUN_DIR / "supervisor.lock"
STOP_FILE = RUN_DIR / "supervisor.stop"

API_BASE_URL = os.getenv("TENNISAGENTS_BETFAIR_API_URL", "http://127.0.0.1:8770")


def _env_int(name: str, default: int, minimum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


CHECK_INTERVAL_SEC = max(
    5, _env_int("TENNISAGENTS_SUPERVISOR_CHECK_SEC", 30, 5)
)
STALE_AFTER_SEC = _env_int("TENNISAGENTS_COLLECTOR_STALE_SEC", 180, 90)
API_START_TIMEOUT_SEC = _env_int("TENNISAGENTS_API_START_TIMEOUT_SEC", 30, 5)
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

log = logging.getLogger("betfairenv.supervisor")


def _setup_logging() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    log.setLevel(logging.INFO)
    log.handlers.clear()
    log.addHandler(handler)
    log.propagate = False


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_suffix(f"{path.suffix}.{os.getpid()}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _request(method: str, path: str, timeout: float = 5.0) -> dict[str, Any] | None:
    request = Request(
        f"{API_BASE_URL}{path}",
        data=b"" if method == "POST" else None,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError, OSError):
        return None
    try:
        result = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return result if isinstance(result, dict) else None


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class InstanceLock:
    """Bloqueo de proceso para impedir dos supervisores simultáneos."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle = None

    def __enter__(self) -> "InstanceLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        if self.handle.tell() == 0:
            self.handle.write(b"0")
            self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.handle.close()
            self.handle = None
            raise RuntimeError("Ya hay un supervisor en ejecución.") from exc
        return self

    def __exit__(self, *_args: object) -> None:
        if self.handle is None:
            return
        try:
            self.handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None


class Supervisor:
    def __init__(self) -> None:
        self.stop_event = threading.Event()
        self.api_process: subprocess.Popen[bytes] | None = None
        self.api_log_handle = None
        self.api_started_at: float | None = None
        self.collector_grace_until = time.monotonic() + STALE_AFTER_SEC
        self.last_health_token: str | None = None
        self.unhealthy_cycles = 0
        self.last_analysis_signature: tuple[Any, ...] | None = None

    def request_stop(self, *_args: object) -> None:
        self.stop_event.set()

    def _api_status(self) -> dict[str, Any] | None:
        return _request("GET", "/api/collector/status")

    def _start_api(self) -> dict[str, Any] | None:
        if self.api_process is not None and self.api_process.poll() is None:
            self.api_process.terminate()
            try:
                self.api_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.api_process.kill()

        env = dict(os.environ)
        python_path = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{ROOT}{os.pathsep}{python_path}" if python_path else str(ROOT)
        )
        if self.api_log_handle is not None:
            self.api_log_handle.close()
        self.api_log_handle = API_LOG_FILE.open("ab")
        self.api_process = subprocess.Popen(
            [sys.executable, "-m", "api.server"],
            cwd=str(ROOT),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=self.api_log_handle,
            stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        self.api_started_at = time.monotonic()
        log.info("API iniciada pid=%s", self.api_process.pid)

        deadline = time.monotonic() + API_START_TIMEOUT_SEC
        while time.monotonic() < deadline and not self.stop_event.is_set():
            status = self._api_status()
            if status is not None:
                return status
            if self.api_process.poll() is not None:
                log.error("La API terminó con código %s", self.api_process.returncode)
                return None
            self.stop_event.wait(1)
        return None

    def _ensure_api(self) -> dict[str, Any] | None:
        status = self._api_status()
        if status is not None:
            return status

        if (
            self.api_process is not None
            and self.api_process.poll() is None
            and self.api_started_at is not None
            and time.monotonic() - self.api_started_at < API_START_TIMEOUT_SEC
        ):
            return None

        log.warning("API no disponible; se intentará recuperar.")
        return self._start_api()

    def _restart_collector(self, reason: str) -> None:
        log.warning("Reiniciando colector: %s", reason)
        _request("POST", "/api/collector/stop", timeout=45)
        if self.stop_event.wait(2):
            return
        started = _request("POST", "/api/collector/start", timeout=15)
        if started and started.get("running"):
            self.collector_grace_until = time.monotonic() + STALE_AFTER_SEC
            log.info("Colector reiniciado pid=%s", started.get("pid"))
        else:
            log.error("No se pudo reiniciar el colector.")

    def _ensure_collector(self, status: dict[str, Any]) -> None:
        if not status.get("running"):
            started = _request("POST", "/api/collector/start", timeout=15)
            if started and started.get("running"):
                self.collector_grace_until = time.monotonic() + STALE_AFTER_SEC
                log.info("Colector iniciado pid=%s", started.get("pid"))
            else:
                log.error("La API no pudo iniciar el colector.")
            return

        if time.monotonic() < self.collector_grace_until:
            return

        analysis_health = status.get("analysis_health") or {}
        analysis_signature = (
            analysis_health.get("status"),
            analysis_health.get("events_unhealthy"),
            analysis_health.get("events_with_backlog"),
        )
        if analysis_signature != self.last_analysis_signature:
            self.last_analysis_signature = analysis_signature
            if analysis_health.get("status") == "degraded":
                log.error(
                    "Análisis degradado: eventos=%s backlog=%s detalles=%s",
                    analysis_health.get("events_unhealthy"),
                    analysis_health.get("events_with_backlog"),
                    analysis_health.get("details"),
                )

        cycle_state = str(status.get("cycle_state") or "")
        health_token = str(
            status.get("last_cycle_at")
            or status.get("cycle_started_at")
            or status.get("heartbeat_at")
            or ""
        )
        if health_token and health_token != self.last_health_token:
            self.last_health_token = health_token
            if cycle_state in {"degraded", "failed"}:
                self.unhealthy_cycles += 1
                log.warning(
                    "Ciclo %s (%s consecutivo/s): snapshots=%s errores=%s %s",
                    cycle_state,
                    self.unhealthy_cycles,
                    status.get("cycle_snapshots"),
                    status.get("cycle_errors"),
                    status.get("cycle_message") or "",
                )
            else:
                self.unhealthy_cycles = 0
            if cycle_state == "failed" and self.unhealthy_cycles >= 3:
                self._restart_collector("tres ciclos fallidos consecutivos")
                self.unhealthy_cycles = 0
                return

        heartbeat = _parse_iso(status.get("heartbeat_at"))
        freshness = heartbeat or _parse_iso(status.get("last_cycle_at"))
        if freshness is None:
            self._restart_collector("no existe heartbeat_at ni last_cycle_at")
            return

        age = (datetime.now(timezone.utc) - freshness).total_seconds()
        if age > STALE_AFTER_SEC:
            self._restart_collector(
                f"heartbeat lleva {int(age)} segundos sin actualizarse"
            )

    def _shutdown(self) -> None:
        _request("POST", "/api/collector/stop", timeout=45)
        if self.api_process is not None and self.api_process.poll() is None:
            self.api_process.terminate()
            try:
                self.api_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.api_process.kill()
        if self.api_log_handle is not None:
            self.api_log_handle.close()
            self.api_log_handle = None
        log.info("Supervisor detenido.")

    def run(self) -> int:
        STOP_FILE.unlink(missing_ok=True)
        _atomic_write(PID_FILE, str(os.getpid()))
        log.info(
            "Supervisor iniciado pid=%s check=%ss stale=%ss",
            os.getpid(),
            CHECK_INTERVAL_SEC,
            STALE_AFTER_SEC,
        )

        def watch_stop_file() -> None:
            while not self.stop_event.wait(1):
                if STOP_FILE.exists():
                    self.request_stop()
                    return

        stop_watcher = threading.Thread(target=watch_stop_file, daemon=True)
        stop_watcher.start()
        try:
            while not self.stop_event.is_set():
                status = self._ensure_api()
                if status is not None:
                    self._ensure_collector(status)
                self.stop_event.wait(CHECK_INTERVAL_SEC)
        except Exception:
            log.exception("Error no controlado en el supervisor.")
            return 1
        finally:
            self._shutdown()
            STOP_FILE.unlink(missing_ok=True)
            PID_FILE.unlink(missing_ok=True)
            stop_watcher.join(timeout=2)
        return 0


def _network_reachable(url: str) -> bool:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=15):
            return True
    except HTTPError:
        # Una respuesta HTTP de bloqueo también demuestra conectividad.
        return True
    except (URLError, TimeoutError, OSError):
        return False


def _llm_available() -> tuple[bool, str | None]:
    try:
        from tennisAgents.default_config import DEFAULT_CONFIG
        from tennisAgents.dataflows.config import set_config
        from tennisAgents.dataflows.llm_utils import get_chat_llm

        set_config(DEFAULT_CONFIG.copy())
        # DeepSeek V4 Flash gasta reasoning tokens; 5 es insuficiente.
        response = get_chat_llm(
            "quick_think_llm",
            timeout=60,
            max_retries=0,
            max_tokens=64,
        ).invoke("Responde solo OK")
        content = getattr(response, "content", "")
        return bool(str(content).strip()), None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _validate(*, network: bool = False, llm: bool = False) -> int:
    write_probe = RUN_DIR / f".supervisor-write-{os.getpid()}.tmp"
    try:
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        write_probe.write_text("ok", encoding="utf-8")
        run_dir_writable = True
    except OSError:
        run_dir_writable = False
    finally:
        write_probe.unlink(missing_ok=True)

    try:
        from dotenv import dotenv_values, find_dotenv

        dotenv_path = find_dotenv()
        dotenv_data = dotenv_values(dotenv_path) if dotenv_path else {}
    except (ImportError, OSError):
        dotenv_path = ""
        dotenv_data = {}
    try:
        from tennisAgents.default_config import DEFAULT_CONFIG

        llm_provider = str(DEFAULT_CONFIG.get("llm_provider") or "openrouter")
        llm_model = str(DEFAULT_CONFIG.get("quick_think_llm") or "")
        llm_backend = str(DEFAULT_CONFIG.get("backend_url") or "")
    except Exception:
        llm_provider = "openrouter"
        llm_model = "deepseek/deepseek-v4-flash"
        llm_backend = "https://openrouter.ai/api/v1"

    credential_by_provider = {
        "openai": "OPENAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
    }
    required_credential = credential_by_provider.get(
        llm_provider.lower(),
        "OPENROUTER_API_KEY",
    )
    credentials_available = bool(
        os.getenv(required_credential) or dotenv_data.get(required_credential)
    )
    checks = {
        "root": str(ROOT),
        "python": sys.executable,
        "api_module": (ROOT / "api" / "server.py").exists(),
        "collector_runner": (ROOT / "collector" / "runner.py").exists(),
        "run_dir_writable": run_dir_writable,
        "dotenv_file": str(dotenv_path) if dotenv_path else None,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "llm_backend": llm_backend,
        "llm_credential_name": required_credential,
        "llm_credentials_available": credentials_available,
        "api_url": API_BASE_URL,
    }
    if network:
        checks["betfair_network"] = _network_reachable("https://www.betfair.es/")
        checks["flashscore_network"] = _network_reachable(
            "https://www.flashscore.es/"
        )
    if llm:
        llm_available, llm_error = _llm_available()
        checks["llm_request_available"] = llm_available
        checks["llm_error"] = llm_error
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    required = (
        checks["api_module"],
        checks["collector_runner"],
        checks["run_dir_writable"],
        checks["llm_credentials_available"],
    )
    if network:
        required += (checks["betfair_network"], checks["flashscore_network"])
    if llm:
        required += (checks["llm_request_available"],)
    return 0 if all(required) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Valida rutas y configuración sin iniciar procesos.",
    )
    parser.add_argument(
        "--network",
        action="store_true",
        help="Comprueba también acceso de red durante --validate.",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Ejecuta una petición mínima real al LLM durante --validate.",
    )
    args = parser.parse_args()
    if args.validate:
        return _validate(network=args.network, llm=args.llm)

    _setup_logging()
    supervisor = Supervisor()
    signal.signal(signal.SIGINT, supervisor.request_stop)
    signal.signal(signal.SIGTERM, supervisor.request_stop)
    try:
        with InstanceLock(LOCK_FILE):
            return supervisor.run()
    except RuntimeError as exc:
        log.info("%s", exc)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
