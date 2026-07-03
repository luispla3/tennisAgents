"""Persistencia de snapshots e índice de partidos."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from collector.anti_block import _interval_bounds, snapshot_interval
from collector.config import TRACK_GRACE_MINUTES
from collector.paths import DATA_DIR

FINISHED_STATUS = ("final", "terminad", "finished", "walkover", "retirad", "abandon")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _snapshot_filename(ts: datetime | None = None) -> str:
    ts = ts or _now_utc()
    return ts.strftime("%Y-%m-%dT%H-%M-%S+00-00") + ".json"


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def index_path() -> Path:
    return DATA_DIR / "index.json"


def match_dir(event_id: str | int) -> Path:
    return DATA_DIR / str(event_id)


def load_index() -> dict[str, Any]:
    path = index_path()
    if not path.exists():
        return {"updated_at": None, "matches": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_index(index: dict[str, Any]) -> None:
    ensure_data_dirs()
    index["updated_at"] = _utc_now_iso()
    index_path().write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def load_meta(event_id: str | int) -> dict[str, Any]:
    path = match_dir(event_id) / "meta.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_meta(event_id: str | int, meta: dict[str, Any]) -> None:
    directory = match_dir(event_id)
    directory.mkdir(parents=True, exist_ok=True)
    meta["updated_at"] = _utc_now_iso()
    (directory / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_snapshot(event_id: str | int, snapshot: dict[str, Any]) -> str:
    directory = match_dir(event_id)
    directory.mkdir(parents=True, exist_ok=True)
    filename = _snapshot_filename(_parse_iso(snapshot.get("timestamp")))
    path = directory / filename
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    meta = load_meta(event_id)
    meta.update(
        {
            "betfair_event_id": snapshot.get("betfair_event_id", meta.get("betfair_event_id")),
            "flashscore_match_id": snapshot.get("flashscore_match_id", meta.get("flashscore_match_id")),
            "last_snapshot_at": snapshot.get("timestamp"),
        }
    )
    snaps = list_snapshots(event_id)
    meta["snapshots_count"] = len(snaps)
    save_meta(event_id, meta)
    return filename


def list_snapshots(event_id: str | int) -> list[dict[str, Any]]:
    directory = match_dir(event_id)
    if not directory.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        if path.name == "meta.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        items.append(
            {
                "file": path.name,
                "timestamp": data.get("timestamp"),
                "score": (data.get("flashscore") or {}).get("score"),
                "status": (data.get("betfair") or {}).get("status")
                or (data.get("flashscore") or {}).get("match", {}).get("status"),
            }
        )
    items.sort(key=lambda x: x.get("timestamp") or "")
    return items


def load_snapshot(event_id: str | int, filename: str) -> dict[str, Any]:
    path = match_dir(event_id) / filename
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_snapshot_timestamp(event_id: str | int) -> str | None:
    snaps = list_snapshots(event_id)
    if not snaps:
        return None
    return snaps[-1].get("timestamp")


def effective_is_live(entry: dict[str, Any]) -> bool:
    if entry.get("finished_at") or entry.get("is_finished"):
        return False
    status = (entry.get("status") or "").lower()
    if any(token in status for token in FINISHED_STATUS):
        return False
    if entry.get("is_live") is False:
        return False
    return entry.get("is_live") is True or "juego" in status


def snapshot_timing_fields(entry: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    now = now or _now_utc()
    last_at = entry.get("last_snapshot_at")
    next_at = entry.get("next_snapshot_at")
    interval = entry.get("snapshot_interval_sec")

    last_dt = _parse_iso(last_at)
    next_dt = _parse_iso(next_at)

    if interval is None and last_dt and next_dt and next_dt > last_dt:
        interval = (next_dt - last_dt).total_seconds()

    if interval is None:
        low, high = _interval_bounds()
        interval = (low + high) / 2

    seconds_until_next = None
    progress = None
    if next_dt:
        remaining = (next_dt - now).total_seconds()
        seconds_until_next = max(0.0, remaining)
        if interval and interval > 0:
            progress = min(100.0, max(0.0, (seconds_until_next / interval) * 100))

    return {
        "seconds_until_next": seconds_until_next,
        "progress": progress,
        "snapshot_interval_sec": interval,
    }


def is_snapshot_due(entry: dict[str, Any], now: datetime | None = None) -> bool:
    if not effective_is_live(entry):
        return False
    if entry.get("queued_for_snapshot"):
        return True
    next_at = entry.get("next_snapshot_at")
    if not next_at:
        return entry.get("last_snapshot_at") is None
    next_dt = _parse_iso(next_at)
    if not next_dt:
        return True
    now = now or _now_utc()
    return now >= next_dt


def seconds_until_earliest_due(now: datetime | None = None) -> float | None:
    now = now or _now_utc()
    index = load_index()
    earliest: float | None = None
    for entry in index.get("matches", {}).values():
        if not is_snapshot_due(entry, now):
            continue
        next_dt = _parse_iso(entry.get("next_snapshot_at"))
        if next_dt is None:
            return 0.0
        remaining = (next_dt - now).total_seconds()
        if earliest is None or remaining < earliest:
            earliest = remaining
    return earliest


def list_all_matches() -> list[dict[str, Any]]:
    index = load_index()
    matches: list[dict[str, Any]] = []
    for event_id, entry in index.get("matches", {}).items():
        meta = load_meta(event_id)
        merged = {**entry, **meta}
        snaps = list_snapshots(event_id)
        timing = snapshot_timing_fields(merged)
        matches.append(
            {
                "event_id": str(event_id),
                "betfair_event_id": merged.get("betfair_event_id"),
                "flashscore_match_id": merged.get("flashscore_match_id"),
                "player1": merged.get("player1"),
                "player2": merged.get("player2"),
                "competition": merged.get("competition"),
                "status": merged.get("status"),
                "is_live": effective_is_live(merged),
                "is_finished": bool(merged.get("is_finished") or merged.get("finished_at")),
                "winner": merged.get("winner"),
                "snapshots_count": len(snaps),
                "first_seen": merged.get("first_seen"),
                "last_seen": merged.get("last_seen"),
                "finished_at": merged.get("finished_at"),
                "last_snapshot_at": merged.get("last_snapshot_at"),
                "next_snapshot_at": merged.get("next_snapshot_at"),
                "snapshot_interval_sec": timing.get("snapshot_interval_sec"),
                "seconds_until_next": timing.get("seconds_until_next"),
                "progress": timing.get("progress"),
                "awaiting_first_snapshot": merged.get("last_snapshot_at") is None and effective_is_live(merged),
                "queued_for_snapshot": bool(merged.get("queued_for_snapshot")),
                "snapshot_due": is_snapshot_due(merged),
                "snapshot_error": merged.get("snapshot_error"),
                "betfair_url": merged.get("betfair_url"),
                "flashscore_url": merged.get("flashscore_url"),
            }
        )
    matches.sort(key=lambda m: (not m.get("is_live", False), m.get("last_seen") or ""), reverse=True)
    return matches


def schedule_next_snapshot(entry: dict[str, Any]) -> dict[str, Any]:
    """Programa el próximo snapshot (usado por el colector)."""
    interval = snapshot_interval()
    now = _now_utc()
    entry["last_snapshot_at"] = entry.get("last_snapshot_at") or _utc_now_iso()
    entry["snapshot_interval_sec"] = interval
    entry["next_snapshot_at"] = (now.timestamp() and datetime.fromtimestamp(
        now.timestamp() + interval, tz=timezone.utc
    ).isoformat())
    entry.pop("queued_for_snapshot", None)
    return entry


def clear_dataset() -> dict[str, Any]:
    """Borra snapshots, metadatos e índice de partidos recolectados."""
    ensure_data_dirs()
    removed_match_dirs = 0
    removed_files = 0

    for path in list(DATA_DIR.iterdir()):
        if path.name == ".gitkeep":
            continue
        if path.is_dir():
            shutil.rmtree(path)
            removed_match_dirs += 1
        elif path.is_file():
            path.unlink()
            removed_files += 1

    index_path().write_text(
        json.dumps({"updated_at": None, "matches": {}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "removed_match_dirs": removed_match_dirs,
        "removed_files": removed_files,
        "message": "Dataset de recolecta borrado",
    }
