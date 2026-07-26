"""Configuración del colector BetfairEnv."""

from __future__ import annotations

import os


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


# Dos minutos de media con jitter suficiente para evitar patrones rígidos.
INTERVAL_BASE_SEC = 120
INTERVAL_JITTER_SEC = 30

REQUEST_DELAY_MIN_SEC = 1.5
REQUEST_DELAY_MAX_SEC = 4.0

SOURCE_GAP_MIN_SEC = 2.0
SOURCE_GAP_MAX_SEC = 5.0

DEFAULT_SPORT = "tennis"
DEFAULT_LOCALE = "es"

TRACK_GRACE_MINUTES = 45
# Sin snapshot reciente y fuera del feed live de Betfair → fantasma histórico.
STALE_SNAPSHOT_HOURS = max(1, _env_int("TENNISAGENTS_STALE_SNAPSHOT_HOURS", 6))
UNREACHABLE_STALE_MINUTES = max(
    30,
    _env_int("TENNISAGENTS_UNREACHABLE_STALE_MINUTES", 120),
)
SNAPSHOT_RETENTION_COUNT = max(
    100,
    _env_int("TENNISAGENTS_SNAPSHOT_RETENTION_COUNT", 20000),
)

API_PORT = 8770
