"""API REST + frontend estático para BetfairEnv."""

from __future__ import annotations

import json
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from api.collector_control import clear_collector_data, collector_status, start_collector, stop_collector
from collector.config import API_PORT
from collector.paths import ROOT
from collector.storage import (
    analysis_health_summary,
    list_all_matches,
    list_snapshots,
    load_index,
    load_meta,
    load_snapshot,
)

STATIC = ROOT / "frontend" / "dist"
FALLBACK_STATIC = ROOT.parent / "web" / "static"
DEFAULT_PORT = API_PORT


def _market_odds_entry(market: dict) -> dict:
    runners = market.get("runners") or []
    odds = {
        r.get("name"): r.get("odds_decimal")
        for r in runners
        if r.get("name")
    }
    return {
        "market_id": market.get("market_id"),
        "name": market.get("name"),
        "market_type": market.get("market_type"),
        "group_name": market.get("group_name"),
        "set_tab": market.get("set_tab"),
        "odds": odds,
    }


def _timeline_markets(betfair: dict) -> list[dict]:
    markets = [_market_odds_entry(m) for m in (betfair.get("markets") or [])]
    primary = betfair.get("primary_market") or {}
    primary_id = primary.get("market_id")
    seen = {m.get("market_id") for m in markets if m.get("market_id")}
    if primary_id and primary_id not in seen:
        markets.insert(0, _market_odds_entry(primary))
    elif not markets and primary:
        markets.append(_market_odds_entry(primary))
    return markets


def _json(handler: SimpleHTTPRequestHandler, payload: object, status: int = HTTPStatus.OK) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _error(handler: SimpleHTTPRequestHandler, message: str, status: int) -> None:
    _json(handler, {"error": message}, status)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        static_dir = STATIC if STATIC.exists() else FALLBACK_STATIC
        super().__init__(*args, directory=str(static_dir), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/collector/"):
            _error(self, "Ruta no encontrada", HTTPStatus.NOT_FOUND)
            return
        action = parsed.path.rstrip("/").split("/")[-1]
        if action == "start":
            _json(self, start_collector())
            return
        if action == "stop":
            _json(self, stop_collector())
            return
        if action in ("clear", "clear-data", "reset"):
            _json(self, clear_collector_data())
            return
        _error(self, f"Acción no válida: {action}", HTTPStatus.BAD_REQUEST)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._api(parsed)
            return
        if parsed.path in ("", "/"):
            self.path = "/index.html"
        super().do_GET()

    def _api(self, parsed) -> None:
        path = parsed.path.rstrip("/")
        parts = [p for p in path.split("/") if p]

        if path == "/api/collector/status":
            status = collector_status()
            index = load_index()
            status["last_index_update"] = index.get("updated_at")
            status["analysis_health"] = analysis_health_summary()
            _json(self, status)
            return

        if path == "/api/matches":
            query = parse_qs(parsed.query or "")
            include_inactive = (query.get("include_inactive") or ["0"])[0].lower() in (
                "1",
                "true",
                "yes",
            )
            matches = list_all_matches(include_inactive=include_inactive)
            _json(self, {"count": len(matches), "matches": matches})
            return

        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "matches":
            event_id = parts[2]
            if not event_id.isdigit():
                _error(self, "ID inválido", HTTPStatus.BAD_REQUEST)
                return

            if len(parts) == 3:
                meta = load_meta(event_id) or {}
                snaps = list_snapshots(event_id)
                _json(self, {"event_id": event_id, "meta": meta, "snapshots": snaps})
                return

            if len(parts) == 5 and parts[3] == "snapshots":
                filename = parts[4]
                snap_path = ROOT / "data" / event_id / filename
                if not snap_path.exists():
                    _error(self, "Snapshot no encontrado", HTTPStatus.NOT_FOUND)
                    return
                _json(self, load_snapshot(event_id, filename))
                return

            if len(parts) == 4 and parts[3] == "timeline":
                timeline = []
                for snap in list_snapshots(event_id):
                    full = load_snapshot(event_id, snap["file"])
                    betfair = full.get("betfair") or {}
                    fs = full.get("flashscore") or {}
                    stats = fs.get("statistics") or {}
                    primary = betfair.get("primary_market") or {}
                    odds = {
                        r.get("name"): r.get("odds_decimal")
                        for r in (primary.get("runners") or [])
                        if r.get("name")
                    }
                    timeline.append(
                        {
                            "timestamp": full.get("timestamp"),
                            "score": fs.get("score"),
                            "sets_won": fs.get("sets_won"),
                            "sets_detail": fs.get("sets_detail"),
                            "current_game": fs.get("current_game"),
                            "current_points": fs.get("current_points") or fs.get("current_game"),
                            "serving": fs.get("serving"),
                            "leading": fs.get("leading"),
                            "winner": fs.get("winner"),
                            "status": betfair.get("status"),
                            "odds": odds,
                            "markets": _timeline_markets(betfair),
                            "stats_overall": stats.get("overall"),
                            "stats_periods": stats.get("periods"),
                            "statistics_error": fs.get("statistics_error"),
                        }
                    )
                _json(self, {"event_id": event_id, "timeline": timeline})
                return

            if len(parts) == 4 and parts[3] == "artifacts":
                event_dir = ROOT / "data" / event_id
                artifacts: dict[str, str] = {}
                artifact_paths = {
                    "context": event_dir / "context.md",
                    "decision": event_dir / "decision.md",
                    "news_report": event_dir / "reports" / "news_report.md",
                    "players_report": event_dir / "reports" / "players_report.md",
                    "tournament_report": event_dir / "reports" / "tournament_report.md",
                    "weather_report": event_dir / "reports" / "weather_report.md",
                }
                for name, artifact_path in artifact_paths.items():
                    if artifact_path.exists():
                        artifacts[name] = artifact_path.read_text(
                            encoding="utf-8"
                        )
                _json(
                    self,
                    {
                        "event_id": event_id,
                        "artifacts": artifacts,
                    },
                )
                return

        _error(self, "Ruta no encontrada", HTTPStatus.NOT_FOUND)


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"BetfairEnv UI: http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAPI detenida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
