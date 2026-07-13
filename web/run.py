"""
Script to run the TennisAgents web server
"""
import socket
import uvicorn
import sys
import os
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.environ.setdefault("PYTHONUTF8", "1")

script_dir = Path(__file__).parent.absolute()
os.chdir(script_dir)

if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))


def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            if sys.platform == "win32":
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            sock.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def pick_port(candidates=(8000, 8001, 8002, 8003, 8010)) -> int:
    """Usa el primer puerto realmente libre (evita zombies en Windows)."""
    for port in candidates:
        if is_port_available(port):
            return port
    return candidates[-1]


if __name__ == "__main__":
    project_root = script_dir.parent
    port = pick_port()

    if port != 8000:
        print(
            f"[AVISO] El puerto 8000 está ocupado (servidor antiguo). "
            f"Usando http://localhost:{port}",
            flush=True,
        )
    else:
        print(f"TennisAgents web: http://localhost:{port}", flush=True)

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
        reload_dirs=[str(script_dir), str(project_root / "tennisAgents")],
    )
