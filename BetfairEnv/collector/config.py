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


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# Mientras el partido no esté finished, no podar (auditoría post-mortem).
SNAPSHOT_PRUNE_ONLY_WHEN_FINISHED = _env_bool(
    "TENNISAGENTS_SNAPSHOT_PRUNE_ONLY_WHEN_FINISHED",
    True,
)
# Tras finished, conservar como máximo este número de snapshots clave.
SNAPSHOT_KEEP_AFTER_FINISH = max(
    5,
    _env_int("TENNISAGENTS_SNAPSHOT_KEEP_AFTER_FINISH", 100),
)
# Borrar directorios de partido fuera del índice activo. OFF por defecto:
# esos dirs son el dataset de training (turns/reports) y no deben purgarse.
PURGE_ORPHAN_MATCH_DIRS = _env_bool(
    "TENNISAGENTS_PURGE_ORPHAN_MATCH_DIRS",
    False,
)

# Hueco entre ciclos completados (p. ej. PC dormido / crash) → aviso en log.
CAPTURE_GAP_WARN_SEC = max(
    60,
    _env_int("TENNISAGENTS_CAPTURE_GAP_WARN_SEC", 300),
)
# Sin snapshots nuevos con partidos activos → alerta operativa.
NO_SNAPSHOT_ALERT_SEC = max(
    120,
    _env_int("TENNISAGENTS_NO_SNAPSHOT_ALERT_SEC", 900),
)
# Tiempo máximo en analysts_running antes de contar missing_reports en health.
ANALYSTS_MAX_RUNTIME_SEC = max(
    60,
    _env_int("TENNISAGENTS_ANALYSTS_MAX_RUNTIME_SEC", 600),
)

API_PORT = 8770
