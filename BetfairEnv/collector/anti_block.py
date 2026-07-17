"""Retrasos aleatorios para reducir bloqueos en scraping."""

from __future__ import annotations

import random
import time

from collector.config import (
    INTERVAL_BASE_SEC,
    INTERVAL_JITTER_SEC,
    REQUEST_DELAY_MAX_SEC,
    REQUEST_DELAY_MIN_SEC,
    SOURCE_GAP_MAX_SEC,
    SOURCE_GAP_MIN_SEC,
)


def _interval_bounds() -> tuple[float, float]:
    low = max(60.0, INTERVAL_BASE_SEC - INTERVAL_JITTER_SEC)
    high = max(low, INTERVAL_BASE_SEC + INTERVAL_JITTER_SEC)
    return low, high


def cycle_interval() -> float:
    """Intervalo del bucle del colector (90–150 s con jitter)."""
    low, high = _interval_bounds()
    return random.uniform(low, high)


def snapshot_interval() -> float:
    """Intervalo hasta el próximo snapshot de un partido (mismo rango, independiente)."""
    return cycle_interval()


def enqueue_stagger_sec() -> float:
    """Retraso inicial al encolar un partido nuevo (0–30 s)."""
    return random.uniform(0, 30)


def pause_between_requests() -> None:
    time.sleep(random.uniform(REQUEST_DELAY_MIN_SEC, REQUEST_DELAY_MAX_SEC))


def pause_between_sources() -> None:
    time.sleep(random.uniform(SOURCE_GAP_MIN_SEC, SOURCE_GAP_MAX_SEC))
