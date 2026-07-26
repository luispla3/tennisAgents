"""Utilidades para resolver fecha/hora del partido desde snapshots."""

from __future__ import annotations

from datetime import datetime, timezone


def _parse_iso_datetime(value: str) -> datetime | None:
    if not value:
        return None
    cleaned = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def resolve_match_datetime(
    match_date: str,
    *,
    snapshot: dict | None = None,
    default_hour: str = "14:00",
) -> str:
    """
    Resuelve la mejor fecha/hora del partido para meteorología.

    Prioridad: Flashscore start_time → start_timestamp → timestamp del snapshot → default.
    """
    if snapshot:
        flashscore = snapshot.get("flashscore") or {}
        match_info = flashscore.get("match") or {}

        start_time = match_info.get("start_time") or flashscore.get("start_time")
        if start_time:
            return str(start_time).strip()

        start_timestamp = match_info.get("start_timestamp") or flashscore.get("start_timestamp")
        if start_timestamp:
            try:
                dt = datetime.fromtimestamp(int(start_timestamp), tz=timezone.utc)
                return dt.strftime("%Y-%m-%d %H:%M")
            except (TypeError, ValueError, OSError):
                pass

        captured_at = snapshot.get("timestamp")
        parsed = _parse_iso_datetime(str(captured_at or ""))
        if parsed and (not match_date or parsed.strftime("%Y-%m-%d") == str(match_date)):
            return parsed.strftime("%Y-%m-%d %H:%M")

    date_part = str(match_date or "").strip() or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hour_part = str(default_hour or "14:00").strip() or "14:00"
    return f"{date_part} {hour_part}"
