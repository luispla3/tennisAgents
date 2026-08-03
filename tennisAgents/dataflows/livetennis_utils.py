"""
Live Tennis API Utilities - fuente OPCIONAL y adicional de datos de partido en vivo.

Esta fuente es totalmente opcional. Si `LIVETENNISAPI_KEY` no está definida, el
módulo se comporta como si no existiera: `livetennis_is_configured()` devuelve
False, no se registra ninguna herramienta y el analista de partidos en vivo sigue
usando Sportradar exactamente igual que antes.

Divulgación: nosotros mantenemos livetennisapi.com.

Flujo:

    fetch_livetennis_match_data(player_a, player_b, tournament)
             ↓
    GET /matches?status=live        (nivel FREE)
             ↓  ¿no está?
    GET /matches?status=upcoming    (nivel FREE)
             ↓  ¿no está?
    GET /matches?status=completed   (requiere BASIC; si no, se omite)
             ↓
    find_livetennis_match()  → reutiliza player_name_matches() de Sportradar
             ↓
    GET /matches/{id}/statistics    (requiere ULTRA; si no, se omite)
             ↓
    format_livetennis_match_report()

Reglas de honestidad que este módulo respeta y que el reporte hace explícitas:
  * Un partido finalizado puede traer `games` vacío. No se inventa un desglose.
  * Las entradas de `points` pueden ser null. Se muestran como "no disponible".
  * En `measured`, un campo ausente se OMITE (no vale cero). Nunca se rellena.
  * `freshness.derived.age_seconds` y `freshness.measured.age_seconds` usan
    relojes distintos y NO deben compararse entre sí.
  * Con `coverage = diverged` los valores medidos se retiran en origen; el
    reporte dice por qué en lugar de mostrar números.
"""

import os
import time
import requests
from dotenv import load_dotenv
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import get_config
from .match_live_utils import normalize_name, player_name_matches

load_dotenv()


# Estados que se recorren, en orden, buscando el partido.
# `completed` requiere nivel BASIC: si la clave no llega, simplemente se omite.
_SEARCH_STATUSES = ("live", "upcoming", "completed")

_NOT_AVAILABLE = "no disponible"


def get_livetennis_api_key() -> Optional[str]:
    """
    Devuelve la API key de Live Tennis API, o None si no está configurada.

    A diferencia de `get_sportradar_api_key()`, esta función NO lanza excepción:
    la fuente es opcional y su ausencia es un estado normal.
    """
    key = os.getenv("LIVETENNISAPI_KEY")
    return key.strip() if key and key.strip() else None


def livetennis_is_configured() -> bool:
    """True solo si hay API key. Sin clave, la herramienta no se registra."""
    return get_livetennis_api_key() is not None


def _base_url() -> str:
    return str(
        get_config().get(
            "livetennis_base_url", "https://api.livetennisapi.com/api/public/v1"
        )
    ).rstrip("/")


def _livetennis_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Hace una petición GET a la Live Tennis API.

    Returns:
        Dict con:
            - success (bool)
            - status (Optional[int]): código HTTP, None si no hubo respuesta
            - data (Any): cuerpo JSON cuando success es True
            - error (str): mensaje cuando success es False
            - error_code (str): código estable de la API (p.ej. upgrade_required)
    """
    api_key = get_livetennis_api_key()
    if not api_key:
        return {
            "success": False,
            "status": None,
            "error": "LIVETENNISAPI_KEY no está configurada",
            "error_code": "not_configured",
        }

    config = get_config()
    url = f"{_base_url()}{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    timeout = config.get("livetennis_api_timeout", 30)
    max_retries = config.get("livetennis_max_retries", 1)

    attempt = 0
    while True:
        try:
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
        except requests.RequestException as exc:
            return {
                "success": False,
                "status": None,
                "error": f"Error de conexión con Live Tennis API: {exc}",
                "error_code": "connection_error",
            }

        # 429: la API manda Retry-After. Se respeta una sola vez y con tope.
        if response.status_code == 429 and attempt < max_retries:
            attempt += 1
            try:
                wait = float(response.headers.get("Retry-After", "1"))
            except ValueError:
                wait = 1.0
            time.sleep(min(max(wait, 0.0), config.get("livetennis_max_retry_wait", 10)))
            continue

        if response.status_code == 200:
            try:
                return {"success": True, "status": 200, "data": response.json()}
            except ValueError:
                return {
                    "success": False,
                    "status": 200,
                    "error": "La respuesta de Live Tennis API no era JSON válido",
                    "error_code": "bad_payload",
                }

        # Errores de la API: {"error": "<codigo>", "detail": "<texto>"}
        error_code, detail = "http_error", ""
        try:
            body = response.json()
            if isinstance(body, dict):
                error_code = str(body.get("error") or error_code)
                detail = str(body.get("detail") or "")
        except ValueError:
            pass

        message = f"Live Tennis API devolvió {response.status_code} ({error_code})"
        if detail:
            message += f": {detail}"

        return {
            "success": False,
            "status": response.status_code,
            "error": message,
            "error_code": error_code,
        }


def fetch_livetennis_matches(status: str, limit: int = 200) -> Dict[str, Any]:
    """Lista partidos por estado de ciclo de vida (`live`, `upcoming`, `completed`)."""
    result = _livetennis_get("/matches", {"status": status, "limit": limit})
    if not result.get("success"):
        return result

    payload = result.get("data") or {}
    matches = payload.get("data") if isinstance(payload, dict) else None
    return {
        "success": True,
        "status": status,
        "matches": matches if isinstance(matches, list) else [],
        "meta": payload.get("meta") if isinstance(payload, dict) else {},
    }


def fetch_livetennis_statistics(match_id: Any) -> Dict[str, Any]:
    """
    Estadísticas en juego de un partido (nivel ULTRA).

    Si la clave no alcanza ese nivel la API responde 403 `upgrade_required`; eso
    NO es un fallo del partido, así que se devuelve como `available: False` con
    el motivo, y el resto del reporte se genera igual.
    """
    result = _livetennis_get(f"/matches/{match_id}/statistics")
    if result.get("success"):
        return {"available": True, "statistics": result.get("data") or {}}

    return {
        "available": False,
        "reason": result.get("error", "Estadísticas no disponibles"),
        "error_code": result.get("error_code", "unknown"),
    }


def _player_name(match: Dict[str, Any], side: str) -> str:
    player = (match.get("players") or {}).get(side) or {}
    return str(player.get("name") or "")


def _tournament_name(match: Dict[str, Any]) -> str:
    return str(match.get("tournament") or "")


def tournament_matches(api_tournament: str, search_tournament: Optional[str]) -> bool:
    """
    Coincidencia laxa de torneo. `tournament` es texto libre en esta API (no hay
    id de torneo), así que solo se usa para desempatar, nunca para descartar de
    forma estricta.
    """
    if not search_tournament:
        return True
    api_norm = normalize_name(api_tournament)
    search_norm = normalize_name(search_tournament)
    if not api_norm or not search_norm:
        return True
    if search_norm in api_norm or api_norm in search_norm:
        return True
    search_words = {w for w in search_norm.split() if len(w) >= 4}
    api_words = {w for w in api_norm.split() if len(w) >= 4}
    return bool(search_words & api_words)


def find_livetennis_match(
    matches: List[Dict[str, Any]],
    player_a: str,
    player_b: str,
    tournament: Optional[str] = None,
    debug: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Busca el partido entre los dos jugadores dentro de una lista ya devuelta por
    la Live Tennis API. La comparación de nombres se hace SOLO dentro de los
    datos de esta API (misma lógica flexible que usa el camino de Sportradar);
    no se cruzan identificadores entre proveedores.

    Si varios partidos encajan, gana el que además cuadra con el torneo.
    """
    candidates: List[Dict[str, Any]] = []

    for match in matches:
        name_1 = _player_name(match, "p1")
        name_2 = _player_name(match, "p2")
        if not name_1 or not name_2:
            continue

        direct = player_name_matches(name_1, player_a, debug=debug) and player_name_matches(
            name_2, player_b, debug=debug
        )
        crossed = player_name_matches(name_1, player_b, debug=debug) and player_name_matches(
            name_2, player_a, debug=debug
        )
        if direct or crossed:
            candidates.append(match)

    if not candidates:
        return None

    for match in candidates:
        if tournament_matches(_tournament_name(match), tournament):
            return match

    return candidates[0]


def _available_matches_text(matches: List[Dict[str, Any]], limit: int = 10) -> str:
    lines = []
    for match in matches[:limit]:
        lines.append(
            f"{_player_name(match, 'p1') or 'N/A'} vs {_player_name(match, 'p2') or 'N/A'} "
            f"({_tournament_name(match) or 'N/A'}) - Estado: {match.get('status', 'N/A')}"
        )
    return "\n".join(lines) if lines else "No hay partidos disponibles"


def fetch_livetennis_match_data(
    player_a: str,
    player_b: str,
    tournament: Optional[str] = None,
    debug: bool = False,
) -> Dict[str, Any]:
    """
    Obtiene los datos de un partido desde la Live Tennis API.

    Returns:
        Dict con el mismo contrato que `fetch_match_live_data()`:
            - success (bool)
            - player_a / player_b / tournament (str)
            - match (Dict): objeto de partido tal cual lo devuelve la API
            - statistics (Dict): resultado de fetch_livetennis_statistics()
            - match_status (str)
            - formatted_data (str): texto estructurado para el agente
            - fetched_at (str)
            - error / note / available_matches / total_live_matches en caso de fallo
    """
    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not livetennis_is_configured():
        return {
            "success": False,
            "error": "LIVETENNISAPI_KEY no está configurada",
            "player_a": player_a,
            "player_b": player_b,
            "tournament": tournament or "N/A",
            "fetched_at": fetched_at,
            "note": "Esta fuente es opcional. Usa la herramienta de Sportradar.",
        }

    first_error: Optional[str] = None
    live_matches: List[Dict[str, Any]] = []
    skipped: List[str] = []

    for status in _SEARCH_STATUSES:
        listing = fetch_livetennis_matches(status)

        if not listing.get("success"):
            # `completed` requiere BASIC: sin nivel suficiente se omite, no falla.
            if listing.get("error_code") == "upgrade_required":
                skipped.append(f"{status} (requiere un nivel superior)")
                continue
            if first_error is None:
                first_error = listing.get("error", "Error al consultar la API")
            continue

        matches = listing.get("matches", [])
        if status == "live":
            live_matches = matches

        found = find_livetennis_match(matches, player_a, player_b, tournament, debug=debug)
        if found:
            statistics = fetch_livetennis_statistics(found.get("id"))
            return {
                "success": True,
                "player_a": player_a,
                "player_b": player_b,
                "tournament": _tournament_name(found) or (tournament or "N/A"),
                "match": found,
                "statistics": statistics,
                "match_status": str(found.get("status") or "unknown"),
                "found_in_status": status,
                "formatted_data": format_livetennis_match_structured(found, statistics),
                "fetched_at": fetched_at,
            }

    if first_error and not live_matches:
        return {
            "success": False,
            "error": first_error,
            "player_a": player_a,
            "player_b": player_b,
            "tournament": tournament or "N/A",
            "fetched_at": fetched_at,
        }

    note = (
        "El partido podría no haber empezado, no estar cubierto, o los nombres no "
        "coinciden con los de esta API. Revisa la lista de partidos disponibles."
    )
    if skipped:
        note += " Estados no consultados por nivel de suscripción: " + ", ".join(skipped) + "."

    return {
        "success": False,
        "error": f"No se encontró el partido entre {player_a} y {player_b}",
        "player_a": player_a,
        "player_b": player_b,
        "tournament": tournament or "N/A",
        "total_live_matches": len(live_matches),
        "available_matches": _available_matches_text(live_matches),
        "fetched_at": fetched_at,
        "note": note,
    }


# ---------------------------------------------------------------------------
# Formateo
# ---------------------------------------------------------------------------


def _show(value: Any) -> str:
    """Un valor ausente se dice, no se convierte en cero."""
    if value is None or value == "":
        return _NOT_AVAILABLE
    return str(value)


def _side_label(side: Any, name_1: str, name_2: str) -> str:
    if side == 1:
        return name_1 or "Jugador 1"
    if side == 2:
        return name_2 or "Jugador 2"
    return _NOT_AVAILABLE


def _format_score(score: Optional[Dict[str, Any]], name_1: str, name_2: str) -> str:
    if not score:
        return "No hay marcador disponible para este partido.\n"

    lines = ["### MARCADOR\n"]

    sets = score.get("sets")
    if isinstance(sets, list) and len(sets) >= 2:
        lines.append(f"- Sets ganados: {name_1} {_show(sets[0])} - {_show(sets[1])} {name_2}")
    else:
        lines.append(f"- Sets ganados: {_NOT_AVAILABLE}")

    # `games` es [games_p1, games_p2], cada uno una lista por set.
    # Un partido finalizado puede traerlo VACÍO: se dice, no se reconstruye.
    games = score.get("games")
    if (
        isinstance(games, list)
        and len(games) == 2
        and isinstance(games[0], list)
        and isinstance(games[1], list)
        and (games[0] or games[1])
    ):
        p1_games, p2_games = games[0], games[1]
        lines.append("- Desglose por set:")
        for index in range(max(len(p1_games), len(p2_games))):
            g1 = p1_games[index] if index < len(p1_games) else None
            g2 = p2_games[index] if index < len(p2_games) else None
            lines.append(f"    Set {index + 1}: {_show(g1)} - {_show(g2)}")
    else:
        lines.append(
            "- Desglose por set: no disponible (la API devolvió un desglose vacío; "
            "no se reconstruye)"
        )

    # Las entradas de `points` pueden ser null.
    points = score.get("points")
    if isinstance(points, list) and len(points) >= 2:
        lines.append(f"- Puntos del juego actual: {_show(points[0])} - {_show(points[1])}")
    else:
        lines.append(f"- Puntos del juego actual: {_NOT_AVAILABLE}")

    lines.append(f"- Al saque: {_side_label(score.get('server'), name_1, name_2)}")
    lines.append(f"- ¿Tie-break en curso?: {'sí' if score.get('is_tiebreak') else 'no'}")
    lines.append(f"- Marcador actualizado (UTC): {_show(score.get('timestamp'))}")

    win_probability = score.get("win_probability_p1")
    if win_probability is not None:
        lines.append(
            f"- Probabilidad de victoria del modelo para {name_1}: {win_probability} "
            "(salida de un modelo, no una cuota de mercado)"
        )

    return "\n".join(lines) + "\n"


# Campos DERIVADOS: reconstruidos del registro punto a punto.
_DERIVED_FIELDS = [
    ("service_games_played", "Juegos de servicio jugados"),
    ("service_games_won", "Juegos de servicio ganados"),
    ("hold_pct", "% de juegos de servicio mantenidos"),
    ("return_games_played", "Juegos al resto jugados"),
    ("return_games_won", "Juegos al resto ganados"),
    ("break_pct", "% de roturas"),
    ("break_points_faced", "Break points en contra"),
    ("break_points_saved", "Break points salvados"),
    ("break_points_saved_pct", "% break points salvados"),
    ("break_points_played", "Break points jugados a favor"),
    ("break_points_converted", "Break points convertidos"),
    ("break_points_converted_pct", "% break points convertidos"),
    ("service_points_played", "Puntos de servicio jugados"),
    ("service_points_won", "Puntos de servicio ganados"),
    ("service_points_won_pct", "% puntos de servicio ganados"),
    ("return_points_played", "Puntos al resto jugados"),
    ("return_points_won", "Puntos al resto ganados"),
    ("return_points_won_pct", "% puntos al resto ganados"),
    ("points_played", "Puntos jugados"),
    ("points_won", "Puntos ganados"),
]

# Campos MEDIDOS: contados aguas arriba. TODOS son opcionales; un campo ausente
# se omite en origen y aquí se muestra como "no disponible", nunca como 0.
_MEASURED_FIELDS = [
    ("aces", "Aces"),
    ("double_faults", "Dobles faltas"),
    ("first_serves_in", "Primeros servicios dentro"),
    ("first_serves_in_of", "Primeros servicios intentados"),
    ("first_serves_in_pct", "% primer servicio dentro"),
    ("first_serve_points_won", "Puntos ganados con 1er servicio"),
    ("first_serve_points_won_of", "Puntos jugados con 1er servicio"),
    ("first_serve_points_won_pct", "% puntos ganados con 1er servicio"),
    ("second_serves_in", "Segundos servicios dentro"),
    ("second_serve_points_won", "Puntos ganados con 2º servicio"),
    ("second_serve_points_won_of", "Puntos jugados con 2º servicio"),
    ("second_serve_points_won_pct", "% puntos ganados con 2º servicio"),
    ("service_games_played", "Juegos de servicio jugados (medido)"),
    ("service_games_won", "Juegos de servicio ganados (medido)"),
    ("service_points_won", "Puntos de servicio ganados (medido)"),
    ("return_points_won", "Puntos al resto ganados (medido)"),
    ("first_return_points_won", "Puntos ganados al resto del 1er servicio"),
    ("second_return_points_won", "Puntos ganados al resto del 2º servicio"),
    ("break_points_won", "Break points ganados (medido)"),
    ("break_points_saved", "Break points salvados (medido)"),
    ("break_points_saved_of", "Break points afrontados (medido)"),
    ("break_points_saved_pct", "% break points salvados (medido)"),
    ("games_won", "Juegos ganados (medido)"),
    ("tiebreaks_won", "Tie-breaks ganados"),
    ("points_won", "Puntos ganados (medido)"),
    ("max_points_in_row", "Máxima racha de puntos"),
    ("max_games_in_row", "Máxima racha de juegos"),
    ("winners_total", "Golpes ganadores"),
    ("unforced_errors_total", "Errores no forzados"),
    ("forehand_winners", "Ganadores de derecha"),
    ("backhand_winners", "Ganadores de revés"),
    ("forehand_unforced_errors", "Errores no forzados de derecha"),
    ("backhand_unforced_errors", "Errores no forzados de revés"),
]


def _format_family(fields, side_1: Dict[str, Any], side_2: Dict[str, Any],
                   name_1: str, name_2: str) -> str:
    lines = [
        f"| Estadística | {name_1 or 'Jugador 1'} | {name_2 or 'Jugador 2'} |",
        "|---|---|---|",
    ]
    for key, label in fields:
        lines.append(f"| {label} | {_show(side_1.get(key))} | {_show(side_2.get(key))} |")
    return "\n".join(lines)


def _format_freshness(freshness: Dict[str, Any]) -> str:
    lines = ["### FRESCURA DE LAS ESTADÍSTICAS\n"]
    lines.append(
        "AVISO: las dos antigüedades usan RELOJES DISTINTOS y no deben compararse "
        "entre sí. La de la familia derivada se mide contra la última fila de "
        "marcador; la de la familia medida es reloj de pared."
    )
    for family in ("derived", "measured"):
        info = freshness.get(family) or {}
        label = "derivada" if family == "derived" else "medida"
        lines.append(
            f"- Familia {label}: cobertura={_show(info.get('coverage'))}, "
            f"as_of={_show(info.get('as_of'))}, antigüedad={_show(info.get('age_seconds'))} s"
        )
        describes = info.get("describes")
        if isinstance(describes, dict):
            lines.append(
                f"    Describe un estado de {_show(describes.get('total_games'))} juegos jugados."
            )

    divergence = freshness.get("measured_divergence")
    if divergence:
        lines.append(
            "- DIVERGENCIA: los valores medidos han sido RETIRADOS en origen. "
            f"Motivo: {_show(divergence.get('reason'))}. "
            f"Juegos en estadísticas={_show(divergence.get('games_in_statistics'))}, "
            f"juegos en marcador={_show(divergence.get('games_in_score'))}. "
            "No los estimes."
        )
    return "\n".join(lines) + "\n"


def _format_statistics(statistics: Dict[str, Any], name_1: str, name_2: str) -> str:
    if not statistics.get("available"):
        return (
            "### ESTADÍSTICAS EN JUEGO\n\n"
            f"No disponibles: {statistics.get('reason', _NOT_AVAILABLE)}\n"
            "No las estimes ni las deduzcas del marcador.\n"
        )

    payload = statistics.get("statistics") or {}
    players = payload.get("players")

    header = ["### ESTADÍSTICAS EN JUEGO\n"]
    header.append(f"- Cobertura global: {_show(payload.get('coverage'))}")
    header.append(f"- Juegos contabilizados: {_show(payload.get('games_counted'))}")
    header.append(
        f"- Tie-breaks excluidos del cálculo derivado: "
        f"{_show(payload.get('tiebreak_games_excluded'))} "
        "(el registro en vivo colapsa el tie-break entero en una sola entrada)"
    )

    freshness = payload.get("freshness")
    if isinstance(freshness, dict):
        header.append("")
        header.append(_format_freshness(freshness))

    if not isinstance(players, dict) or not players:
        header.append(
            "\nNo se dispone de estadísticas para este partido "
            f"({_show(payload.get('detail'))}). El partido existe; simplemente no "
            "hay números que dar. No los inventes.\n"
        )
        return "\n".join(header)

    side_1 = players.get("p1") or {}
    side_2 = players.get("p2") or {}

    body = [
        "",
        "#### Familia DERIVADA (reconstruida del registro punto a punto)",
        "",
        _format_family(_DERIVED_FIELDS, side_1, side_2, name_1, name_2),
        "",
        "#### Familia MEDIDA (contada aguas arriba)",
        "",
        "Ambas familias nombran algunas de las mismas magnitudes calculadas de dos "
        "maneras distintas: eso es una comprobación cruzada, no una duplicación que "
        "haya que fusionar. Un campo marcado como 'no disponible' NO vale cero.",
        "",
        _format_family(
            _MEASURED_FIELDS,
            side_1.get("measured") or {},
            side_2.get("measured") or {},
            name_1,
            name_2,
        ),
        "",
    ]
    return "\n".join(header + body)


def format_livetennis_match_structured(
    match: Dict[str, Any], statistics: Optional[Dict[str, Any]] = None
) -> str:
    """Convierte el partido de la Live Tennis API en texto estructurado."""
    statistics = statistics or {"available": False, "reason": "no consultadas"}

    name_1 = _player_name(match, "p1") or "Jugador 1"
    name_2 = _player_name(match, "p2") or "Jugador 2"
    players = match.get("players") or {}
    player_1 = players.get("p1") or {}
    player_2 = players.get("p2") or {}

    lines = [
        "## DATOS DEL PARTIDO (Live Tennis API)\n",
        "### INFORMACIÓN BÁSICA\n",
        f"- Torneo: {_show(match.get('tournament'))} "
        "(texto libre: esta API no expone id de torneo ni sede)",
        f"- Superficie: {_show(match.get('surface'))}",
        f"- Pista cubierta: {'sí' if match.get('indoor') else 'no'}",
        f"- Formato: {_show(match.get('format'))}",
        f"- Ronda: {_show(match.get('round'))}",
        f"- Estado: {_show(match.get('status'))} "
        f"(detalle: {_show(match.get('event_status'))})",
        f"- Dobles: {'sí' if match.get('is_doubles') else 'no'}",
        f"- Hora programada (UTC): {_show(match.get('scheduled_time'))}",
        "",
        "### JUGADORES\n",
        f"- Jugador 1: {name_1} | país: {_show(player_1.get('country'))} | "
        f"ranking actual: {_show(player_1.get('ranking'))} | "
        f"mano: {_show(player_1.get('hand'))}",
        f"- Jugador 2: {name_2} | país: {_show(player_2.get('country'))} | "
        f"ranking actual: {_show(player_2.get('ranking'))} | "
        f"mano: {_show(player_2.get('hand'))}",
        "  (el ranking es el valor ACTUAL del jugador, no el que tenía el día del partido)",
        "",
    ]

    winner = match.get("winner")
    if winner is not None:
        lines.append(f"- Ganador: {_side_label(winner, name_1, name_2)}")
        lines.append("")

    lines.append(_format_score(match.get("score"), name_1, name_2))
    lines.append("")
    lines.append(_format_statistics(statistics, name_1, name_2))

    return "\n".join(lines)


def format_livetennis_match_report(match_data: Dict[str, Any]) -> str:
    """Formatea el resultado de `fetch_livetennis_match_data()` para el agente."""
    if not match_data or match_data.get("success") is False:
        result = "## Error al Obtener Datos del Partido (Live Tennis API)\n\n"
        result += f"**Error:** {match_data.get('error', 'Error desconocido')}\n\n"
        result += f"**Jugadores:** {match_data.get('player_a', 'N/A')} vs {match_data.get('player_b', 'N/A')}\n"
        result += f"**Torneo:** {match_data.get('tournament', 'N/A')}\n"
        result += f"**Fecha:** {match_data.get('fetched_at', 'N/A')}\n"

        note = match_data.get("note")
        if note:
            result += f"\n**Nota:** {note}\n"
        if match_data.get("total_live_matches") is not None:
            result += f"\n**Partidos en vivo encontrados:** {match_data.get('total_live_matches')}\n"
        available = match_data.get("available_matches")
        if available:
            result += f"\n**Partidos disponibles:**\n{available}\n"
        return result

    result = "## 🎾 Partido en Vivo - Live Tennis API\n\n"
    result += f"**Consultado el:** {match_data.get('fetched_at', 'N/A')}\n"
    result += f"**Encontrado en el listado:** {match_data.get('found_in_status', 'N/A')}\n\n"
    result += match_data.get("formatted_data", "No se pudieron formatear los datos")
    result += (
        "\n\n---\n"
        "**Fuente:** Live Tennis API (https://livetennisapi.com)\n"
        "**Límites conocidos de esta fuente:** no ofrece head-to-head, ni cuotas de "
        "casa de apuestas, ni estadísticas de saque/resto por jugador a nivel de "
        "carrera, ni datos de torneo o sede. Cualquier campo marcado como "
        "'no disponible' significa exactamente eso: no lo rellenes ni lo estimes.\n"
    )
    return result
