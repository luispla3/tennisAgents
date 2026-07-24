"""Persistencia de snapshots e índice de partidos."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from collector.anti_block import _interval_bounds, snapshot_interval
from collector.config import SNAPSHOT_RETENTION_COUNT, TRACK_GRACE_MINUTES
from collector.paths import DATA_DIR

FINISHED_STATUS = ("final", "terminad", "finished", "walkover", "retirad", "abandon")
_META_LOCKS_GUARD = threading.Lock()
_META_LOCKS: dict[str, threading.Lock] = {}


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
    return ts.strftime("%Y-%m-%dT%H-%M-%S-%f+00-00") + ".json"


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_write_text(path: Path, content: str) -> None:
    """Escribe un archivo sin dejar JSON/Markdown parcialmente escrito."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.{os.getpid()}-{threading.get_ident()}-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink(missing_ok=True)


def index_path() -> Path:
    return DATA_DIR / "index.json"


def index_backup_path() -> Path:
    return DATA_DIR / "index.backup.json"


def match_dir(event_id: str | int) -> Path:
    return DATA_DIR / str(event_id)


def load_index() -> dict[str, Any]:
    for candidate in (index_path(), index_backup_path()):
        if not candidate.exists():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return data
    return {"updated_at": None, "matches": {}}


def save_index(index: dict[str, Any]) -> None:
    ensure_data_dirs()
    current_path = index_path()
    index["updated_at"] = _utc_now_iso()
    content = json.dumps(index, ensure_ascii=False, indent=2)
    _atomic_write_text(
        current_path,
        content,
    )
    _atomic_write_text(index_backup_path(), content)


def load_meta(event_id: str | int) -> dict[str, Any]:
    directory = match_dir(event_id)
    for path in (directory / "meta.json", directory / "meta.backup.json"):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return data
    return {}


def save_meta(
    event_id: str | int,
    meta: dict[str, Any],
    *,
    replace: bool = False,
    remove_keys: tuple[str, ...] = (),
    preserve_existing_keys: tuple[str, ...] = (),
) -> None:
    directory = match_dir(event_id)
    directory.mkdir(parents=True, exist_ok=True)
    event_key = str(event_id)
    with _META_LOCKS_GUARD:
        event_lock = _META_LOCKS.setdefault(event_key, threading.Lock())
    with event_lock:
        existing = load_meta(event_id)
        merged = dict(meta) if replace else {**existing, **meta}
        for key in preserve_existing_keys:
            if key in existing:
                merged[key] = existing[key]
        for key in remove_keys:
            merged.pop(key, None)
        merged["updated_at"] = _utc_now_iso()
        content = json.dumps(merged, ensure_ascii=False, indent=2)
        _atomic_write_text(directory / "meta.json", content)
        _atomic_write_text(directory / "meta.backup.json", content)


def save_snapshot(event_id: str | int, snapshot: dict[str, Any]) -> str:
    directory = match_dir(event_id)
    directory.mkdir(parents=True, exist_ok=True)
    filename = _snapshot_filename(_parse_iso(snapshot.get("timestamp")))
    path = directory / filename
    was_existing = path.exists()
    _atomic_write_text(
        path,
        json.dumps(snapshot, ensure_ascii=False, indent=2),
    )

    meta = load_meta(event_id)
    try:
        snapshot_count = int(meta.get("snapshots_count"))
    except (TypeError, ValueError):
        snapshot_count = -1
    if snapshot_count < 0:
        snapshot_count = len(list_snapshot_files(event_id))
    elif not was_existing:
        snapshot_count += 1

    # Se poda en lotes para no ordenar miles de archivos en cada snapshot.
    prune_threshold = SNAPSHOT_RETENTION_COUNT + max(100, SNAPSHOT_RETENTION_COUNT // 20)
    if snapshot_count > prune_threshold:
        last_processed = str(meta.get("last_processed_snapshot_at") or "")
        snapshot_items = {
            item["file"]: str(item.get("timestamp") or "")
            for item in list_snapshot_files(event_id)
        }
        snapshot_paths = sorted(
            (
                candidate
                for candidate in directory.glob("*.json")
                if candidate.name not in {"meta.json", "meta.backup.json"}
            ),
            key=lambda candidate: candidate.name,
        )
        excess = len(snapshot_paths) - SNAPSHOT_RETENTION_COUNT
        pruned = 0
        for old_path in snapshot_paths:
            if pruned >= max(0, excess):
                break
            timestamp = snapshot_items.get(old_path.name, "")
            if not last_processed or not timestamp or timestamp > last_processed:
                continue
            try:
                old_path.unlink()
                snapshot_count -= 1
                pruned += 1
            except OSError:
                pass
        if pruned < max(0, excess):
            meta["snapshot_retention_blocked"] = {
                "at": _utc_now_iso(),
                "reason": "No se eliminan snapshots pendientes de análisis.",
                "pending_excess": max(0, excess) - pruned,
            }
        else:
            meta.pop("snapshot_retention_blocked", None)

    collector_update = {
        "betfair_event_id": snapshot.get(
            "betfair_event_id",
            meta.get("betfair_event_id"),
        ),
        "flashscore_match_id": snapshot.get(
            "flashscore_match_id",
            meta.get("flashscore_match_id"),
        ),
        "last_snapshot_at": snapshot.get("timestamp"),
        "snapshots_count": snapshot_count,
    }
    if meta.get("snapshot_retention_blocked"):
        collector_update["snapshot_retention_blocked"] = meta[
            "snapshot_retention_blocked"
        ]
    save_meta(
        event_id,
        collector_update,
        remove_keys=(
            ()
            if meta.get("snapshot_retention_blocked")
            else ("snapshot_retention_blocked",)
        ),
    )
    return filename


def list_snapshots(event_id: str | int) -> list[dict[str, Any]]:
    directory = match_dir(event_id)
    if not directory.exists():
        return []
    items: list[dict[str, Any]] = []
    for item in list_snapshot_files(event_id):
        path = directory / item["file"]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        items.append(
            {
                "file": item["file"],
                "timestamp": data.get("timestamp"),
                "score": (data.get("flashscore") or {}).get("score"),
                "status": (data.get("betfair") or {}).get("status")
                or (data.get("flashscore") or {}).get("match", {}).get("status"),
            }
        )
    items.sort(key=lambda x: x.get("timestamp") or "")
    return items


def list_snapshot_files(event_id: str | int) -> list[dict[str, str]]:
    """Lista snapshots sin leer su contenido, para colas de larga duración."""
    directory = match_dir(event_id)
    if not directory.exists():
        return []
    items: list[dict[str, str]] = []
    for path in sorted(directory.glob("*.json")):
        if path.name in {"meta.json", "meta.backup.json"}:
            continue
        timestamp = None
        for timestamp_format in (
            "%Y-%m-%dT%H-%M-%S-%f+00-00",
            "%Y-%m-%dT%H-%M-%S+00-00",
        ):
            try:
                timestamp = datetime.strptime(
                    path.stem,
                    timestamp_format,
                ).replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue
        items.append(
            {
                "file": path.name,
                "timestamp": timestamp.isoformat() if timestamp else path.stem,
            }
        )
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
        snaps = list_snapshot_files(event_id)
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
                "is_stale": bool(merged.get("is_stale") or merged.get("stale_at")),
                "winner": merged.get("winner"),
                "snapshots_count": len(snaps),
                "first_seen": merged.get("first_seen"),
                "last_seen": merged.get("last_seen"),
                "finished_at": merged.get("finished_at"),
                "stale_at": merged.get("stale_at"),
                "last_snapshot_at": merged.get("last_snapshot_at"),
                "next_snapshot_at": merged.get("next_snapshot_at"),
                "snapshot_interval_sec": timing.get("snapshot_interval_sec"),
                "seconds_until_next": timing.get("seconds_until_next"),
                "progress": timing.get("progress"),
                "awaiting_first_snapshot": merged.get("last_snapshot_at") is None and effective_is_live(merged),
                "queued_for_snapshot": bool(merged.get("queued_for_snapshot")),
                "snapshot_due": is_snapshot_due(merged),
                "snapshot_error": merged.get("snapshot_error"),
                "analysis_status": merged.get("analysis_status"),
                "analysts_completed": bool(merged.get("analysts_completed")),
                "last_analysis_step": merged.get("last_analysis_step"),
                "last_analysis_at": merged.get("last_analysis_at"),
                "last_processed_snapshot_at": merged.get("last_processed_snapshot_at"),
                "analysis_current_snapshot_at": merged.get("analysis_current_snapshot_at"),
                "analysis_error": merged.get("analysis_error"),
                "analysis_degraded_reason": merged.get("analysis_degraded_reason"),
                "available_balance": merged.get("available_balance"),
                "open_positions_count": len(merged.get("open_positions") or []),
                "realized_pnl": merged.get("realized_pnl"),
                "settlement_status": merged.get("settlement_status"),
                "context_file": str((match_dir(event_id) / "context.md").relative_to(DATA_DIR)).replace("\\", "/")
                if (match_dir(event_id) / "context.md").exists()
                else None,
                "betfair_url": merged.get("betfair_url"),
                "flashscore_url": merged.get("flashscore_url"),
            }
        )
    matches.sort(key=lambda m: (not m.get("is_live", False), m.get("last_seen") or ""), reverse=True)
    return matches


def analysis_health_summary() -> dict[str, Any]:
    """Resumen O(partidos activos), sin recorrer históricos ni snapshots."""
    index_matches = load_index().get("matches") or {}
    unhealthy: list[dict[str, Any]] = []
    backlog = 0
    for raw_event_id, entry in sorted(index_matches.items()):
        event_id = str(raw_event_id)
        meta = load_meta(event_id)
        status = str(meta.get("analysis_status") or "")
        # Partidos ya cerrados no deben ensuciar la salud operativa.
        if status.startswith("finished"):
            continue
        last_snapshot = _parse_iso(
            meta.get("last_snapshot_at") or entry.get("last_snapshot_at")
        )
        last_processed = _parse_iso(meta.get("last_processed_snapshot_at"))
        has_backlog = bool(
            last_snapshot
            and (
                last_processed is None
                or (last_snapshot - last_processed).total_seconds() > 0.5
            )
        )
        if has_backlog:
            backlog += 1
        error = meta.get("analysis_error")
        retention_blocked = meta.get("snapshot_retention_blocked")
        reports_dir = match_dir(event_id) / "reports"
        expected_reports = (
            "news_report.md",
            "players_report.md",
            "tournament_report.md",
            "weather_report.md",
        )
        missing_reports = []
        if meta.get("analysis_started_at") and status not in {
            "",
            "idle",
            "pending",
        }:
            for report_name in expected_reports:
                report_path = reports_dir / report_name
                try:
                    usable = report_path.exists() and report_path.stat().st_size >= 1000
                except OSError:
                    usable = False
                if not usable:
                    missing_reports.append(report_name)
        # "degraded" histórico por policy_rejected ya no se usa; solo errores reales.
        if error or status in {"error"} or missing_reports or retention_blocked:
            unhealthy.append(
                {
                    "event_id": event_id,
                    "status": status or None,
                    "error": error,
                    "missing_reports": missing_reports,
                    "has_backlog": has_backlog,
                    "snapshot_retention_blocked": retention_blocked,
                }
            )

    return {
        "status": "degraded" if unhealthy else "ok",
        "events_total": len(index_matches),
        "events_unhealthy": len(unhealthy),
        "historical_events_unhealthy": 0,
        "events_with_backlog": backlog,
        "details": unhealthy[:50],
    }


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

    _atomic_write_text(
        index_path(),
        json.dumps({"updated_at": None, "matches": {}}, ensure_ascii=False, indent=2),
    )

    return {
        "removed_match_dirs": removed_match_dirs,
        "removed_files": removed_files,
        "message": "Dataset de recolecta borrado",
    }
