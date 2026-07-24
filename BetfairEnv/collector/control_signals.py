"""Señales cooperativas de control del colector."""

from __future__ import annotations

import threading
from pathlib import Path


def watch_stop_file(
    stop_event: threading.Event,
    stop_file: Path,
    *,
    poll_interval_sec: float = 1.0,
) -> None:
    """Convierte la señal IPC por archivo en un cierre cooperativo."""
    while not stop_event.wait(poll_interval_sec):
        if stop_file.exists():
            stop_event.set()
            return
