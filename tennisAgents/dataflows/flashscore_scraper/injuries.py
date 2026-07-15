"""Historial de lesiones de jugadores desde Flashscore."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Optional

from tennisAgents.dataflows.flashscore_scraper.client import FlashscoreClient, FlashscoreError
from tennisAgents.dataflows.match_live_utils import player_name_matches


def _extract_json_object(text: str, key: str) -> Optional[dict[str, Any]]:
    marker = f'"{key}":'
    idx = text.find(marker)
    if idx == -1:
        return None
    start = text.find("{", idx + len(marker))
    if start == -1:
        return None
    depth = 0
    for pos, char in enumerate(text[start:], start=start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : pos + 1])
                except json.JSONDecodeError:
                    return None
    return None


def parse_player_profile_slug(pm_feed: str) -> Optional[str]:
    """Extrae slug/id del feed pm (p. ej. van-de-zandschulp-botic/YwiLpILD)."""
    match = re.search(r"/player/([a-z0-9-]+)/([A-Za-z0-9]{8})", pm_feed)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    return None


def parse_injuries_from_html(html: str) -> list[dict[str, Any]]:
    """Parsea injury_history embebido en teamPageEnvironment."""
    injuries_block = _extract_json_object(html, "injuries")
    if not injuries_block:
        return []
    history = injuries_block.get("injury_history") or []
    parsed: list[dict[str, Any]] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        if item.get("hide"):
            continue
        parsed.append(
            {
                "from": str(item.get("injury_from", "")).strip(),
                "to": str(item.get("injury_until", "")).strip(),
                "description": str(item.get("injury_name", "")).strip(),
            }
        )
    return parsed


def _collect_matches(day_offsets: range) -> list[dict[str, Any]]:
    from tennisAgents.dataflows.flashscore_scraper import get_matches

    matches: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for offset in day_offsets:
        try:
            day_matches = get_matches("tennis", day_offset=offset)
        except FlashscoreError:
            continue
        for match in day_matches:
            match_id = match.get("id")
            if match_id and match_id in seen_ids:
                continue
            if match_id:
                seen_ids.add(match_id)
            matches.append(match)
    return matches


def resolve_flashscore_player(
    player_name: str,
    opponent_name: Optional[str] = None,
) -> Optional[tuple[str, str]]:
    """Resuelve (player_id, nombre_flashscore) buscando en partidos recientes."""
    for match in _collect_matches(range(-7, 8)):
        for name_key, id_key in (("player1", "player1_id"), ("player2", "player2_id")):
            api_name = match.get(name_key, "")
            if not player_name_matches(api_name, player_name):
                continue
            if opponent_name:
                other_key = "player2" if name_key == "player1" else "player1"
                if not player_name_matches(match.get(other_key, ""), opponent_name):
                    continue
            player_id = match.get(id_key)
            if player_id:
                return str(player_id), str(api_name)
    return None


def fetch_player_injuries(
    player_name: str,
    opponent_name: Optional[str] = None,
    locale: str = "es",
) -> dict[str, Any]:
    """Obtiene historial de lesiones de un jugador vía Flashscore."""
    resolved = resolve_flashscore_player(player_name, opponent_name)
    if not resolved:
        return {
            "player_name": player_name,
            "flashscore_name": None,
            "player_id": None,
            "injuries": [],
            "error": "No se encontró el jugador en partidos Flashscore recientes.",
        }

    player_id, flashscore_name = resolved
    client = FlashscoreClient(locale=locale)

    try:
        pm_feed = client.get_player_meta(player_id)
    except FlashscoreError as exc:
        return {
            "player_name": player_name,
            "flashscore_name": flashscore_name,
            "player_id": player_id,
            "injuries": [],
            "error": str(exc),
        }

    slug = parse_player_profile_slug(pm_feed)
    if not slug:
        return {
            "player_name": player_name,
            "flashscore_name": flashscore_name,
            "player_id": player_id,
            "injuries": [],
            "error": "No se pudo resolver la URL del perfil Flashscore.",
        }

    profile_segment = "jugador" if locale == "es" else "player"
    url = f"{client.base_url}/{profile_segment}/{slug}/"

    try:
        html = client._get_text(url)
    except FlashscoreError as exc:
        return {
            "player_name": player_name,
            "flashscore_name": flashscore_name,
            "player_id": player_id,
            "injuries": [],
            "error": str(exc),
        }

    injuries = parse_injuries_from_html(html)
    return {
        "player_name": player_name,
        "flashscore_name": flashscore_name,
        "player_id": player_id,
        "injuries": injuries,
        "source_url": url,
        "error": None,
    }


def _parse_flashscore_date(value: str) -> Optional[datetime]:
    try:
        return datetime.strptime(value, "%d.%m.%Y")
    except ValueError:
        return None


def _format_player_injury_section(result: dict[str, Any]) -> str:
    display_name = result.get("flashscore_name") or result.get("player_name") or "Jugador"
    lines = [f"### {display_name}"]

    if result.get("error"):
        lines.append(f"Estado: {result['error']}")
        return "\n".join(lines)

    injuries: list[dict[str, Any]] = result.get("injuries") or []
    if not injuries:
        lines.append("Historial de lesiones: sin registros en Flashscore.")
        return "\n".join(lines)

    lines.append("Fuente: Flashscore")
    if result.get("source_url"):
        lines.append(f"URL: {result['source_url']}")
    lines.append("")
    lines.append("| Desde | Hasta | Lesión |")
    lines.append("| --- | --- | --- |")
    for item in injuries:
        lines.append(f"| {item.get('from', '-')} | {item.get('to', '-')} | {item.get('description', '-')} |")

    today = datetime.now()
    recent: list[str] = []
    for item in injuries:
        end = _parse_flashscore_date(str(item.get("to", "")))
        start = _parse_flashscore_date(str(item.get("from", "")))
        ref = end or start
        if ref and (today - ref).days <= 365:
            recent.append(f"- {item.get('from')} -> {item.get('to')}: {item.get('description')}")

    if recent:
        lines.append("")
        lines.append("Ausencias en los últimos 12 meses:")
        lines.extend(recent)

    return "\n".join(lines)


def format_injury_reports(player1_name: str, player2_name: str, locale: str = "es") -> str:
    """Genera informe de lesiones para ambos jugadores del partido."""
    r1 = fetch_player_injuries(player1_name, opponent_name=player2_name, locale=locale)
    r2 = fetch_player_injuries(player2_name, opponent_name=player1_name, locale=locale)

    sections = [
        "# HISTORIAL DE LESIONES (Flashscore)",
        "",
        _format_player_injury_section(r1),
        "",
        _format_player_injury_section(r2),
    ]
    return "\n".join(sections)
