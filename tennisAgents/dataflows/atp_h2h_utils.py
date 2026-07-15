"""Head-to-head determinista desde la API interna de ATP Tour."""

from __future__ import annotations

from typing import Any

import requests

from tennisAgents.dataflows.tennis_abstract_utils import fetch_player_profile, resolve_player_name

ATP_BASE = "https://www.atptour.com"
ATP_API_BASE = "https://edx.atptour.com"
H2H_API = f"{ATP_API_BASE}/en/-/www/h2h/{{player1_id}}/{{player2_id}}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def _player_team(data: dict[str, Any], side: str) -> dict[str, Any]:
    return data.get(f"PlayerTeam{side}", {}) or {}


def _resolve_atp_player_id(name: str) -> dict[str, Any]:
    profile = fetch_player_profile(name)
    if not profile.get("found"):
        return {
            "input_name": name,
            "resolved_name": resolve_player_name(name),
            "found": False,
            "error": "Perfil no encontrado en Tennis Abstract para obtener el ID ATP.",
        }

    atp_id = (profile.get("atp_id") or "").strip()
    if not atp_id:
        return {
            "input_name": name,
            "resolved_name": profile.get("resolved_name") or resolve_player_name(name),
            "found": False,
            "error": "No se pudo resolver el ID ATP del jugador.",
        }

    return {
        "input_name": name,
        "resolved_name": profile.get("resolved_name") or resolve_player_name(name),
        "found": True,
        "atp_id": atp_id.upper(),
        "profile_source": profile.get("source"),
    }


def fetch_atp_h2h(player1_name: str, player2_name: str) -> dict[str, Any]:
    """Consulta H2H oficial ATP usando IDs ATP resueltos desde Tennis Abstract."""
    p1 = _resolve_atp_player_id(player1_name)
    p2 = _resolve_atp_player_id(player2_name)

    if not p1.get("found") or not p2.get("found"):
        return {
            "found": False,
            "player1": p1,
            "player2": p2,
            "source": f"{ATP_BASE}/en/players/atp-head-2-head",
        }

    url = H2H_API.format(player1_id=p1["atp_id"], player2_id=p2["atp_id"])
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    data = response.json()

    return {
        "found": True,
        "player1": p1,
        "player2": p2,
        "source": f"{ATP_BASE}{data.get('showDetailLink', '/en/players/atp-head-2-head')}",
        "api_source": url,
        "data": data,
    }


def _bio_lines(label: str, left: Any, right: Any) -> str:
    return f"- {label}: {left} | {right}"


def _player_bio(player: dict[str, Any]) -> dict[str, str]:
    backhand = (player.get("BackHand") or {}).get("Description") or "N/D"
    return {
        "rank": str(player.get("Ranking") or "N/D"),
        "age": str(player.get("Age") or "N/D"),
        "weight": f"{player.get('WeightLb', 'N/D')}lbs ({player.get('WeightKg', 'N/D')}kg)",
        "height": f"{player.get('HeightFt', 'N/D')} ({player.get('HeightCm', 'N/D')}cm)",
        "plays": player.get("PlayHandDisplayFormat") or "N/D",
        "backhand": backhand,
        "turned_pro": str(player.get("ProYear") or "N/D"),
        "ytd_wl": f"{player.get('YearToDateWins', 0)}/{player.get('YearToDateLosses', 0)}",
        "ytd_titles": str(player.get("YearToDateTitles") if player.get("YearToDateTitles") is not None else "N/D"),
        "career_wl": f"{player.get('SglCareerWon', 0)}/{player.get('SglCareerLost', 0)}",
        "career_titles": str(player.get("CareerTitles") if player.get("CareerTitles") is not None else "N/D"),
        "prize_money": player.get("CareerPrizeMoneyFormatted") or "N/D",
        "country": player.get("PlayerCountryCode") or "N/D",
    }


def _format_score_string(result_string: str) -> str:
    return (result_string or "N/D").strip()


def format_atp_h2h_report(player1_name: str, player2_name: str) -> str:
    try:
        payload = fetch_atp_h2h(player1_name, player2_name)
    except Exception as exc:
        return f"Error al consultar head-to-head ATP: {exc}"

    if not payload.get("found"):
        p1 = payload.get("player1", {})
        p2 = payload.get("player2", {})
        return (
            "## Head-to-head (ATP Tour)\n\n"
            f"No se pudo resolver el H2H oficial entre `{player1_name}` y `{player2_name}`.\n"
            f"- Jugador 1: {p1.get('resolved_name', player1_name)} -> {p1.get('error', 'N/D')}\n"
            f"- Jugador 2: {p2.get('resolved_name', player2_name)} -> {p2.get('error', 'N/D')}\n"
            f"- Fuente: {payload.get('source')}"
        )

    data = payload["data"]
    team1 = _player_team(data, "1")
    team2 = _player_team(data, "2")
    bio1 = _player_bio(team1)
    bio2 = _player_bio(team2)

    lines = [
        "## Head-to-head (ATP Tour)",
        "",
        f"- Jugador 1 recibido: {payload['player1']['input_name']} -> {team1.get('PlayerFullName')}",
        f"- Jugador 2 recibido: {payload['player2']['input_name']} -> {team2.get('PlayerFullName')}",
        f"- Marcador H2H ATP: {team1.get('PlayerFullName')} {team1.get('Record', 0)} - {team2.get('Record', 0)} {team2.get('PlayerFullName')}",
        f"- Fuente web: {payload['source']}",
        f"- Fuente API: {payload['api_source']}",
        "",
        "### Comparativa Bio",
        _bio_lines("Ranking ATP", bio1["rank"], bio2["rank"]),
        _bio_lines("Edad", bio1["age"], bio2["age"]),
        _bio_lines("Peso", bio1["weight"], bio2["weight"]),
        _bio_lines("Altura", bio1["height"], bio2["height"]),
        _bio_lines("Mano", bio1["plays"], bio2["plays"]),
        _bio_lines("Revés", bio1["backhand"], bio2["backhand"]),
        _bio_lines("Turned Pro", bio1["turned_pro"], bio2["turned_pro"]),
        _bio_lines("YTD W/L", bio1["ytd_wl"], bio2["ytd_wl"]),
        _bio_lines("YTD títulos", bio1["ytd_titles"], bio2["ytd_titles"]),
        _bio_lines("Carrera W/L", bio1["career_wl"], bio2["career_wl"]),
        _bio_lines("Títulos ATP", bio1["career_titles"], bio2["career_titles"]),
        _bio_lines("Premios carrera", bio1["prize_money"], bio2["prize_money"]),
        "",
    ]

    tournaments = data.get("Tournaments") or []
    other = data.get("OtherTournaments") or []
    all_events = tournaments + other

    if not all_events:
        lines.extend([
            "### Event breakdown",
            "- No hay enfrentamientos previos registrados en ATP Tour entre estos jugadores.",
            "- Este será su primer H2H oficial según la base de datos ATP.",
            "",
        ])
        return "\n".join(lines).strip()

    record1 = team1.get("Record", 0) or 0
    record2 = team2.get("Record", 0) or 0
    if record1 == 0 and record2 == 0:
        lines.extend([
            "- **Nota:** El marcador global ATP muestra 0-0, pero el desglose inferior "
            "lista enfrentamientos concretos. Prioriza el event breakdown como fuente principal.",
            "",
        ])

    lines.extend(["### Event breakdown", ""])
    lines.append("| Año | Torneo | Superficie | Ronda | Ganador | Marcador |")
    lines.append("| --- | --- | --- | --- | --- | --- |")

    id_to_name = {
        team1.get("PlayerId", "").upper(): team1.get("PlayerFullName", "Jugador 1"),
        team2.get("PlayerId", "").upper(): team2.get("PlayerFullName", "Jugador 2"),
    }

    for event in all_events:
        for match in event.get("Matches") or []:
            winner_id = (match.get("Winner") or "").upper()
            winner_name = id_to_name.get(winner_id, winner_id or "N/D")
            round_name = (match.get("Round") or {}).get("ShortName") or "N/D"
            lines.append(
                "| {year} | {tournament} | {surface} | {round_} | {winner} | {score} |".format(
                    year=event.get("EventYear", "N/D"),
                    tournament=event.get("EventDisplayName") or event.get("EventName") or "N/D",
                    surface=event.get("Surface") or "N/D",
                    round_=round_name,
                    winner=winner_name,
                    score=_format_score_string(match.get("ResultString") or ""),
                )
            )

    lines.append("")
    return "\n".join(lines).strip()
