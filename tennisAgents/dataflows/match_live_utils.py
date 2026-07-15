"""
Match Live Utilities - Datos en tiempo real de partidos usando Flashscore scraper.
"""

from __future__ import annotations

import json
import unicodedata
from datetime import datetime
from typing import Any, Dict, Optional

from tennisAgents.dataflows.flashscore_scraper import (
    get_live_matches,
    get_match_statistics,
    get_matches,
)
from tennisAgents.dataflows.flashscore_scraper.client import FlashscoreError
from tennisAgents.dataflows.match_filters import filter_singles_male_matches


def normalize_name(name: str) -> str:
    nfkd_form = unicodedata.normalize("NFKD", name)
    normalized = "".join(c for c in nfkd_form if not unicodedata.combining(c))
    return normalized.lower().strip()


def player_name_matches(api_name: str, search_name: str, debug: bool = False) -> bool:
    api_normalized = normalize_name(api_name)
    search_normalized = normalize_name(search_name)

    if debug:
        print(f"          Comparando: API='{api_normalized}' vs Search='{search_normalized}'")

    if search_normalized in api_normalized or api_normalized in search_normalized:
        return True

    if "," in api_name:
        parts = [normalize_name(p.strip()) for p in api_name.split(",")]
        reversed_name = " ".join(reversed(parts))
        if search_normalized in reversed_name or reversed_name in search_normalized:
            return True

    search_words = {w for w in search_normalized.split() if len(w) >= 3}
    api_words = {w for w in api_normalized.replace(",", " ").split() if len(w) >= 3}
    if search_words & api_words:
        return True

    return False


def tournament_name_matches(api_tournament: str, search_tournament: str, debug: bool = False) -> bool:
    api_normalized = normalize_name(api_tournament)
    search_normalized = normalize_name(search_tournament)

    translations = {
        "masculino": "men",
        "femenino": "women",
        "viena": "vienna",
        "munich": "munchen",
        "praga": "prague",
    }
    for spanish, english in translations.items():
        search_normalized = search_normalized.replace(spanish, english)
        api_normalized = api_normalized.replace(spanish, english)

    if search_normalized in api_normalized or api_normalized in search_normalized:
        return True

    search_words = [w for w in search_normalized.split() if len(w) >= 3]
    api_words = {w for w in api_normalized.split() if len(w) >= 3}
    if search_words:
        matches = sum(1 for word in search_words if word in api_words)
        if matches / len(search_words) >= 0.5:
            return True

    return False


def _collect_matches(live_only: bool = False) -> list[dict[str, Any]]:
    try:
        if live_only:
            matches = get_live_matches("tennis")
            if matches:
                return filter_singles_male_matches(matches)
        matches = get_matches("tennis", live_only=live_only)
        return filter_singles_male_matches(matches)
    except FlashscoreError as exc:
        print(f"[ERROR] Flashscore: {exc}")
        return []


def fetch_live_summaries(include_all_statuses: bool = False) -> Dict[str, Any]:
    """Compatibilidad con endpoints web: devuelve partidos en vivo o del día."""
    try:
        matches = _collect_matches(live_only=not include_all_statuses)
        fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {
            "success": True,
            "data": {"matches": matches},
            "total_matches": len(matches),
            "fetched_at": fetched_at,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "data": {"matches": []},
            "total_matches": 0,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


def fetch_daily_summaries(
    date: Optional[str] = None,
    access_level: str = "trial",
    language_code: str = "en",
    format: str = "json",
) -> Dict[str, Any]:
    """Partidos del día desde Flashscore."""
    del access_level, language_code, format
    try:
        matches = get_matches("tennis", day_offset=0, live_only=False)
        current_date = date or datetime.now().strftime("%Y-%m-%d")
        return {
            "success": True,
            "data": {"matches": matches},
            "date": current_date,
            "total_matches": len(matches),
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except FlashscoreError as exc:
        return {
            "success": False,
            "error": str(exc),
            "data": {"matches": []},
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "total_matches": 0,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


def fetch_season_summaries(
    season_id: str,
    access_level: str = "trial",
    language_code: str = "en",
    format: str = "json",
) -> Dict[str, Any]:
    """Ya no aplica con Flashscore; se mantiene por compatibilidad de la API web."""
    del season_id, access_level, language_code, format
    return {
        "success": False,
        "error": "Season summaries no disponible con Flashscore scraper.",
        "data": {},
        "total_matches": 0,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def find_match_in_summaries(
    summaries_data: Dict[str, Any],
    player_a: str,
    player_b: str,
    tournament: Optional[str] = None,
    debug: bool = True,
) -> Optional[Dict[str, Any]]:
    if not summaries_data.get("success"):
        return None

    matches = summaries_data.get("data", {}).get("matches", [])
    print(f"\n[INFO] Buscando partido entre '{player_a}' y '{player_b}'")

    if debug and matches:
        print(f"\n[DEBUG] ===== PARTIDOS DISPONIBLES ({len(matches)}) =====")
        for idx, match in enumerate(matches, 1):
            print(
                f"  [{idx}] {match.get('player1')} vs {match.get('player2')} | "
                f"{match.get('status')} | {match.get('tournament', 'N/A')}"
            )
        print("[DEBUG] ==========================================\n")

    for match in matches:
        names = [match.get("player1", ""), match.get("player2", "")]
        player_a_found = any(player_name_matches(name, player_a, debug=debug) for name in names)
        player_b_found = any(player_name_matches(name, player_b, debug=debug) for name in names)

        if player_a_found and player_b_found:
            if tournament:
                if not tournament_name_matches(match.get("tournament", ""), tournament, debug=debug):
                    continue
            print(f"\n[SUCCESS] Partido encontrado: {names[0]} vs {names[1]}")
            return match

    print(f"\n[WARNING] No se encontró el partido entre '{player_a}' y '{player_b}'")
    return None


def list_all_live_matches() -> str:
    summaries_data = fetch_live_summaries()
    if not summaries_data.get("success"):
        return f"Error al obtener partidos: {summaries_data.get('error', 'Error desconocido')}"

    matches = summaries_data.get("data", {}).get("matches", [])
    if not matches:
        return "No hay partidos en vivo en este momento."

    result = f"# PARTIDOS EN VIVO ({len(matches)} encontrados)\n\n"
    for idx, match in enumerate(matches, 1):
        result += (
            f"{idx}. {match.get('player1')} vs {match.get('player2')}\n"
            f"   Torneo: {match.get('tournament', 'N/A')}\n"
            f"   Estado: {match.get('status', 'N/A')}\n"
            f"   Marcador: {match.get('score', '-')}\n\n"
        )
    return result


def fetch_match_live_data(
    player_a: str,
    player_b: str,
    tournament: Optional[str] = None,
    debug: bool = True,
) -> Dict[str, Any]:
    try:
        print(f"\n[INFO] Buscando partido en Flashscore: {player_a} vs {player_b}")

        summaries_data = fetch_live_summaries(include_all_statuses=False)
        match = find_match_in_summaries(summaries_data, player_a, player_b, tournament, debug=debug)

        if not match:
            summaries_data = fetch_live_summaries(include_all_statuses=True)
            match = find_match_in_summaries(summaries_data, player_a, player_b, tournament, debug=debug)

        if not match:
            available = summaries_data.get("data", {}).get("matches", [])[:10]
            available_list = "\n".join(
                f"{m.get('player1')} vs {m.get('player2')} ({m.get('tournament', 'N/A')})"
                for m in available
            )
            return {
                "success": False,
                "error": f"No se encontró el partido entre {player_a} y {player_b}",
                "player_a": player_a,
                "player_b": player_b,
                "tournament": tournament or "N/A",
                "available_matches": available_list or "No hay partidos disponibles",
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        stats = {}
        if match.get("has_stats") or match.get("is_live"):
            try:
                stats = get_match_statistics(match["id"])
            except FlashscoreError as exc:
                print(f"[WARNING] No se pudieron obtener estadísticas: {exc}")

        formatted_data = format_match_data_structured(match, stats)
        return {
            "success": True,
            "player_a": player_a,
            "player_b": player_b,
            "tournament": match.get("tournament", tournament or "N/A"),
            "match_data": match,
            "match_stats": stats,
            "match_status": "live" if match.get("is_live") else match.get("status", "unknown"),
            "formatted_data": formatted_data,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Error al obtener datos del partido: {exc}",
            "player_a": player_a,
            "player_b": player_b,
            "tournament": tournament or "N/A",
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


def format_match_data_structured(match: Dict[str, Any], stats: Optional[Dict[str, Any]] = None) -> str:
    try:
        is_live = match.get("is_live", False)
        status = match.get("status", "Desconocido")
        result = "# DATOS DEL PARTIDO (Flashscore)\n\n"

        if is_live:
            result += "✅ **PARTIDO EN VIVO**\n\n"
        else:
            result += f"⚠️ **Estado:** {status}\n\n"

        result += "---\n\n"
        result += "## 1. INFORMACIÓN BÁSICA DEL PARTIDO\n\n"
        result += f"**Jugador 1:** {match.get('player1', 'N/A')}\n"
        result += f"**Jugador 2:** {match.get('player2', 'N/A')}\n"
        result += f"**Torneo:** {match.get('tournament', 'N/A')}\n"
        result += f"**Categoría:** {match.get('category', 'N/A')}\n"
        result += f"**ID del partido:** {match.get('id', 'N/A')}\n"
        if match.get("start_time"):
            result += f"**Hora de inicio:** {match.get('start_time')}\n"
        if match.get("url"):
            result += f"**Enlace:** {match.get('url')}\n"
        result += "\n"

        result += "## 2. MARCADOR ACTUAL\n\n"
        result += f"**Marcador por sets:** {match.get('score', 'N/A')}\n"
        sets_won = match.get("sets_won") or {}
        if sets_won:
            result += (
                f"**Sets ganados:** {match.get('player1')} {sets_won.get('player1', 0)} - "
                f"{sets_won.get('player2', 0)} {match.get('player2')}\n"
            )
        result += "\n"

        result += "## 3. ESTADÍSTICAS DETALLADAS\n\n"
        if stats and stats.get("overall"):
            for stat_name, values in stats["overall"].items():
                result += (
                    f"- **{stat_name}:** {match.get('player1')} {values.get('home', '-')} | "
                    f"{match.get('player2')} {values.get('away', '-')}\n"
                )
            result += "\n"
        else:
            result += "*No hay estadísticas detalladas disponibles para este partido*\n\n"

        if stats and stats.get("periods"):
            result += "### Desglose por periodos\n\n"
            for period in stats["periods"]:
                result += f"**{period.get('name', 'Periodo')}**\n"
                for stat in period.get("stats", []):
                    result += (
                        f"- {stat.get('name')}: {stat.get('home', '-')} / {stat.get('away', '-')}\n"
                    )
                result += "\n"

        result += "---\n"
        result += "*Datos obtenidos del scraper de Flashscore*\n"
        return result
    except Exception as exc:
        return (
            f"## Error al formatear datos del partido\n\n**Error:** {exc}\n\n"
            f"```json\n{json.dumps(match, indent=2, ensure_ascii=False)}\n```"
        )


def format_match_live_report(match_data: Dict[str, Any]) -> str:
    if not match_data or match_data.get("success") is False:
        error_msg = match_data.get("error", "Error desconocido")
        result = "## Error al Obtener Datos del Partido en Vivo\n\n"
        result += f"**Error:** {error_msg}\n\n"
        result += f"**Jugadores:** {match_data.get('player_a', 'N/A')} vs {match_data.get('player_b', 'N/A')}\n"
        result += f"**Torneo:** {match_data.get('tournament', 'N/A')}\n"
        if match_data.get("available_matches"):
            result += f"\n**Partidos disponibles:**\n{match_data['available_matches']}\n"
        return result

    return match_data.get("formatted_data", "No se pudieron formatear los datos")
