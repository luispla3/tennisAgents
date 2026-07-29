"""Utilidades de apagado del colector (void de posiciones, etc.)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from collector import storage as storage_module
from tennisAgents.default_config import DEFAULT_CONFIG

log = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _void_position(
    *,
    position: dict[str, Any],
    available_balance: float,
    history: list[dict[str, Any]],
    reason: str,
) -> float:
    stake = _safe_float(
        position.get("remaining_stake", position.get("initial_stake")),
        0.0,
    )
    available_balance += stake
    history.append(
        {
            "event": "voided",
            "position_id": position.get("position_id"),
            "voided_at": _utc_now_iso(),
            "stake": stake,
            "pnl": 0.0,
            "reason": reason,
        }
    )
    return available_balance


def void_open_positions_on_shutdown(config: dict[str, Any] | None = None) -> int:
    """
    Devuelve stakes de posiciones que sigan abiertas al detener el colector.

    El runner intenta antes Close/settlement (`settle_open_positions_on_shutdown`);
    esta función es el fallback (también tras taskkill desde la API).
    """
    cfg = config or DEFAULT_CONFIG
    if not cfg.get("void_open_positions_on_shutdown", True):
        return 0
    data_dir = storage_module.DATA_DIR
    if not data_dir.exists():
        return 0

    voided = 0
    default_wallet = _safe_float(cfg.get("automated_wallet_balance"), 100.0)
    reason = (
        "Sistema detenido con posición abierta; "
        "stake devuelto (void) al apagar el colector."
    )

    for directory in data_dir.iterdir():
        if not directory.is_dir() or not directory.name.isdigit():
            continue
        event_id = directory.name
        meta = storage_module.load_meta(event_id)
        open_positions = [
            position
            for position in (meta.get("open_positions") or [])
            if isinstance(position, dict)
        ]
        if not open_positions:
            continue

        history = list(meta.get("position_history") or [])
        available_balance = _safe_float(
            meta.get("available_balance", meta.get("wallet_balance", default_wallet)),
            default_wallet,
        )
        for position in open_positions:
            available_balance = _void_position(
                position=position,
                available_balance=available_balance,
                history=history,
                reason=reason,
            )
            voided += 1

        meta["open_positions"] = []
        meta["position_history"] = history
        meta["available_balance"] = round(available_balance, 8)
        # No pisar un settlement previo del drain si no quedaban posiciones.
        if meta.get("settlement_status") != "settled_on_shutdown":
            meta["settlement_status"] = "voided_on_shutdown"
        if meta.get("analysis_status") not in {
            "finished",
            "finished_unsettled",
            "stopped_settled",
        }:
            meta["analysis_status"] = "stopped_unsettled"
        storage_module.save_meta(event_id, meta)

    if voided:
        log.info("Posiciones anuladas al apagar el colector: %s", voided)
    return voided
