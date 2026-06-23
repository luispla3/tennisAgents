"""Parser del formato pipe-delimited de Flashscore."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

ROW_END = "~"
CELL_END = "¬"
INDEX = "÷"

# Índices compartidos
EVENT_ID = "AA"
EVENT_STAGE_TYPE = "AB"  # 1=finished, 2=live, 3=scheduled
EVENT_STAGE = "AC"
WINNER_SIDE = "AW"
HOME_SETS_WON = "AG"
AWAY_SETS_WON = "AH"
START_TIME = "AD"
TOURNAMENT = "ZA"
PLAYER1_NAME = "CX"
PLAYER2_NAME = "AF"
PLAYER1_ID = "PX"
PLAYER2_ID = "PY"
LIVE_FLAG = "AI"
HAS_STATS = "AO"
HOME_SCORE = "AG"
AWAY_SCORE = "AH"
HOME_SET1, HOME_SET2, HOME_SET3, HOME_SET4, HOME_SET5 = "BA", "BC", "BE", "BG", "BI"
AWAY_SET1, AWAY_SET2, AWAY_SET3, AWAY_SET4, AWAY_SET5 = "BB", "BD", "BF", "BH", "BJ"

# Estadísticas
STATS_SET = "SE"
STATS_GROUP = "SG"
STATS_HOME = "SH"
STATS_AWAY = "SI"

STAGE_LABELS = {
    1: "Finalizado",
    2: "En juego",
    3: "Programado",
    4: "Pospuesto",
    5: "Cancelado",
    6: "Abandonado",
    7: "Walkover",
    8: "Retirado",
}

FINISHED_STAGE_TYPES = {1, 6, 7, 8}

HOME_SET_KEYS = [HOME_SET1, HOME_SET2, HOME_SET3, HOME_SET4, HOME_SET5]
AWAY_SET_KEYS = [AWAY_SET1, AWAY_SET2, AWAY_SET3, AWAY_SET4, AWAY_SET5]


def _split_rows(content: str) -> list[list[str]]:
    rows = []
    for row in content.split(ROW_END):
        if not row.strip():
            continue
        rows.append([cell for cell in row.split(CELL_END) if cell])
    return rows


def _parse_cells(cells: list[str]) -> dict[str, str]:
    data: dict[str, str] = {}
    for cell in cells:
        if INDEX not in cell:
            continue
        key, value = cell.split(INDEX, 1)
        data[key] = value
    return data


def _format_score(data: dict[str, str], *, swap: bool = False) -> str:
    sets = []
    home_keys = HOME_SET_KEYS
    away_keys = AWAY_SET_KEYS
    if swap:
        home_keys, away_keys = away_keys, home_keys
    for hk, ak in zip(home_keys, away_keys):
        if hk in data or ak in data:
            sets.append(f"{data.get(hk, '0')}-{data.get(ak, '0')}")
    if sets:
        return " ".join(sets)
    if HOME_SCORE in data or AWAY_SCORE in data:
        home = data.get(HOME_SCORE, "0")
        away = data.get(AWAY_SCORE, "0")
        if swap:
            home, away = away, home
        return f"{home}-{away}"
    return ""


def _sets_won(data: dict[str, str], *, swap: bool = False) -> tuple[int | None, int | None]:
    if HOME_SETS_WON not in data and AWAY_SETS_WON not in data:
        return None, None
    home = int(data.get(HOME_SETS_WON, "0") or "0")
    away = int(data.get(AWAY_SETS_WON, "0") or "0")
    if swap:
        home, away = away, home
    return home, away


def _winner_from_data(
    data: dict[str, str],
    player1: str,
    player2: str,
    *,
    swap: bool = False,
) -> str | None:
    home_sets, away_sets = _sets_won(data, swap=swap)
    if home_sets is not None and away_sets is not None and home_sets != away_sets:
        return player1 if home_sets > away_sets else player2
    return None


def _build_result_summary(
    *,
    winner: str | None,
    loser: str | None,
    score: str,
    status: str,
    sets_won: tuple[int | None, int | None] = (None, None),
) -> str:
    if status == "Walkover" and winner:
        return f"Walkover — ganó {winner}"
    if status == "Retirado" and winner:
        return f"Retirada — ganó {winner}"
    if status == "Abandonado" and winner:
        return f"Abandonado — ganó {winner}"

    if winner and score:
        return f"Ganó {winner} {score}"
    if winner and sets_won[0] is not None and sets_won[1] is not None:
        p1_sets, p2_sets = sets_won
        return f"Ganó {winner} ({p1_sets}-{p2_sets} en sets)"
    if winner:
        return f"Ganó {winner}"
    if score:
        return f"Finalizado {score}"
    if status == "Finalizado":
        return "Finalizado (marcador pendiente)"
    return status


def _row_has_score(data: dict[str, str]) -> bool:
    if any(key in data for key in HOME_SET_KEYS):
        return True
    return HOME_SETS_WON in data or AWAY_SETS_WON in data


def _row_score_rank(data: dict[str, str]) -> int:
    rank = 0
    if _row_has_score(data):
        rank += 10 + sum(1 for key in HOME_SET_KEYS if key in data)
    if HOME_SETS_WON in data or AWAY_SETS_WON in data:
        rank += 5
    return rank


def _match_score_rank(match: dict[str, Any]) -> int:
    rank = 0
    score = match.get("score", "")
    if score:
        rank += 20 + score.count(" ")
    sw = match.get("sets_won") or {}
    if sw.get("player1") is not None:
        rank += 5
    if match.get("is_finished"):
        rank += 3
    if not match.get("is_live"):
        rank += 1
    return rank


def dedupe_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fusiona filas duplicadas del feed conservando la más completa."""
    by_id: dict[str, dict[str, Any]] = {}
    for match in matches:
        match_id = match["id"]
        current = by_id.get(match_id)
        if current is None or _match_score_rank(match) > _match_score_rank(current):
            by_id[match_id] = match
    return list(by_id.values())


def has_decisive_sets_won(match: dict[str, Any]) -> bool:
    sw = match.get("sets_won") or {}
    p1 = sw.get("player1")
    p2 = sw.get("player2")
    return p1 is not None and p2 is not None and p1 != p2


def has_decisive_score(match: dict[str, Any]) -> bool:
    """True si el partido ya tiene un marcador completo en el feed diario."""
    if has_decisive_sets_won(match):
        return True
    score = match.get("score", "")
    return bool(score and " " in score)


def is_finished_tennis_match(match: dict[str, Any]) -> bool:
    """Partido terminado: AB=1/6/7/8 o AB=3 con resultado definitivo (no en juego)."""
    if match.get("is_live"):
        return False
    if match.get("is_finished"):
        return True
    if has_decisive_sets_won(match):
        return True
    score = match.get("score", "")
    if match.get("stage_type") == 3 and score:
        parts = score.split()
        if len(parts) >= 2:
            return True
        if has_decisive_sets_won(match):
            return True
    return False


def parse_scoreboard_feed(content: str) -> dict[str, str] | None:
    """Extrae marcador por sets desde df_su (filas con BA/BB, BC/BD, ...)."""
    merged: dict[str, str] = {}
    for cells in _split_rows(content):
        data = _parse_cells(cells)
        if not data:
            continue
        for home_key, away_key in zip(HOME_SET_KEYS, AWAY_SET_KEYS):
            if home_key in data or away_key in data:
                merged[home_key] = data.get(home_key, "0")
                merged[away_key] = data.get(away_key, "0")

    if not merged:
        return None

    p1_sets = 0
    p2_sets = 0
    for home_key, away_key in zip(HOME_SET_KEYS, AWAY_SET_KEYS):
        if home_key not in merged and away_key not in merged:
            continue
        home = int(merged.get(home_key, "0") or "0")
        away = int(merged.get(away_key, "0") or "0")
        if home > away:
            p1_sets += 1
        elif away > home:
            p2_sets += 1

    if p1_sets == p2_sets:
        return None

    merged[HOME_SETS_WON] = str(p1_sets)
    merged[AWAY_SETS_WON] = str(p2_sets)
    return merged


def parse_dc_score(data: dict[str, str]) -> dict[str, str] | None:
    """Reconstruye sets desde el feed dc cuando DA=3 y hay juegos registrados."""
    if data.get("DA") != "3":
        return None

    p1_sets = int(data.get("DE", "0") or "0")
    p2_sets = int(data.get("DF", "0") or "0")
    if p1_sets == p2_sets or p1_sets + p2_sets == 0:
        return None

    dn = int(data.get("DN", "0") or "0")
    do = int(data.get("DO", "0") or "0")
    dp = int(data.get("DP", "0") or "0")
    dq = int(data.get("DQ", "0") or "0")
    if dn == 0 and do == 0:
        return None

    result: dict[str, str] = {
        HOME_SET1: str(dn),
        AWAY_SET1: str(do),
        HOME_SETS_WON: str(p1_sets),
        AWAY_SETS_WON: str(p2_sets),
    }

    if p1_sets + p2_sets >= 2:
        set2_home = dp - dn
        set2_away = dq - do
        if set2_home >= 0 and set2_away >= 0 and (set2_home > 0 or set2_away > 0):
            result[HOME_SET2] = str(set2_home)
            result[AWAY_SET2] = str(set2_away)

    if _format_score(result):
        return result
    return None


def merge_player_feed_index(
    indexed: dict[str, dict[str, str]],
    content: str,
) -> None:
    for cells in _split_rows(content):
        data = _parse_cells(cells)
        match_id = data.get(EVENT_ID)
        if not match_id:
            continue
        current = indexed.get(match_id)
        if current is None or _row_score_rank(data) > _row_score_rank(current):
            indexed[match_id] = data


def _index_feed_matches(content: str) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    for cells in _split_rows(content):
        data = _parse_cells(cells)
        match_id = data.get(EVENT_ID)
        if match_id:
            indexed[match_id] = data
    return indexed


def _apply_score_source(
    enriched: dict[str, Any],
    source: dict[str, str],
    *,
    swap: bool = False,
) -> None:
    enriched["score"] = _format_score(source, swap=swap)
    p1_sets, p2_sets = _sets_won(source, swap=swap)
    if p1_sets is not None:
        enriched["sets_won"] = {"player1": p1_sets, "player2": p2_sets}


def enrich_finished_match(
    match: dict[str, Any],
    player_feeds: dict[str, dict[str, dict[str, str]]],
    extra_sources: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Completa marcador y ganador usando historial, df_su y dc."""
    enriched = dict(match)
    source: dict[str, str] | None = None
    swap = False

    if not enriched.get("score"):
        for player_key, player_id in (
            ("player1_id", enriched.get("player1_id")),
            ("player2_id", enriched.get("player2_id")),
        ):
            if not player_id:
                continue
            feed = player_feeds.get(str(player_id), {})
            row = feed.get(enriched["id"])
            if row and _row_has_score(row):
                source = row
                swap = player_key == "player2_id"
                break

    if not source and extra_sources:
        source = extra_sources.get(enriched["id"])

    if source and not enriched.get("score"):
        _apply_score_source(enriched, source, swap=swap)

    p1_sets = (enriched.get("sets_won") or {}).get("player1")
    p2_sets = (enriched.get("sets_won") or {}).get("player2")
    if (p1_sets is None or p2_sets is None) and source:
        p1_sets, p2_sets = _sets_won(source, swap=swap)

    winner = _winner_from_data(
        source or {},
        enriched.get("player1", ""),
        enriched.get("player2", ""),
        swap=swap,
    )
    if not winner and p1_sets is not None and p2_sets is not None and p1_sets != p2_sets:
        winner = enriched["player1"] if p1_sets > p2_sets else enriched["player2"]

    loser = None
    if winner:
        loser = enriched["player2"] if winner == enriched.get("player1") else enriched.get("player1")

    enriched["winner"] = winner
    enriched["loser"] = loser
    enriched["result"] = _build_result_summary(
        winner=winner,
        loser=loser,
        score=enriched.get("score", ""),
        status=enriched.get("status", "Finalizado"),
        sets_won=(p1_sets, p2_sets),
    )
    return enriched


def parse_feed(content: str) -> list[dict[str, Any]]:
    """Convierte el feed diario en lista de partidos."""
    matches: list[dict[str, Any]] = []
    current_tournament = ""
    current_category = ""

    for cells in _split_rows(content):
        data = _parse_cells(cells)
        if not data:
            continue

        if TOURNAMENT in data:
            raw = data[TOURNAMENT]
            current_tournament = raw
            current_category = raw.split(" - ")[0] if " - " in raw else raw
            continue

        if EVENT_ID not in data:
            continue

        stage_type = int(data.get(EVENT_STAGE_TYPE, "0") or "0")
        match: dict[str, Any] = {
            "id": data[EVENT_ID],
            "tournament": current_tournament,
            "category": current_category,
            "player1": data.get(PLAYER1_NAME, ""),
            "player2": data.get(PLAYER2_NAME, ""),
            "player1_id": data.get(PLAYER1_ID, ""),
            "player2_id": data.get(PLAYER2_ID, ""),
            "start_timestamp": int(data[START_TIME]) if START_TIME in data else None,
            "stage_type": stage_type,
            "status": STAGE_LABELS.get(stage_type, f"Estado {stage_type}"),
            "is_live": stage_type == 2,
            "is_finished": stage_type in FINISHED_STAGE_TYPES,
            "is_scheduled": stage_type == 3,
            "has_stats": data.get(HAS_STATS) == "1",
            "score": _format_score(data),
            "url": f"https://www.flashscore.es/partido/{data[EVENT_ID]}/",
        }

        p1_sets, p2_sets = _sets_won(data)
        if p1_sets is not None:
            match["sets_won"] = {"player1": p1_sets, "player2": p2_sets}

        if match["start_timestamp"]:
            dt = datetime.fromtimestamp(match["start_timestamp"])
            match["start_time"] = dt.strftime("%Y-%m-%d %H:%M")

        matches.append(match)

    return matches


def parse_stats(content: str) -> dict[str, Any]:
    """Parsea estadísticas de un partido (df_st)."""
    result: dict[str, Any] = {"periods": [], "overall": {}}
    current_period: Optional[dict[str, Any]] = None
    current_stat: Optional[dict[str, str]] = None

    for cells in _split_rows(content):
        data = _parse_cells(cells)
        if not data:
            continue

        if STATS_SET in data:
            if current_period and current_stat:
                current_period.setdefault("stats", []).append(current_stat)
                current_stat = None
            if current_period:
                result["periods"].append(current_period)
            current_period = {"name": data[STATS_SET], "stats": []}
            continue

        if STATS_GROUP in data:
            if current_period and current_stat:
                current_period["stats"].append(current_stat)
            current_stat = {
                "name": data[STATS_GROUP],
                "home": data.get(STATS_HOME, ""),
                "away": data.get(STATS_AWAY, ""),
            }
            continue

        if current_stat:
            if STATS_HOME in data:
                current_stat["home"] = data[STATS_HOME]
            if STATS_AWAY in data:
                current_stat["away"] = data[STATS_AWAY]

    if current_period:
        if current_stat:
            current_period["stats"].append(current_stat)
        result["periods"].append(current_period)

    # Resumen global: buscar periodo "Match" o el último conjunto de stats
    for period in result["periods"]:
        name = period["name"].lower()
        if name in ("match", "partido", "overall", "total"):
            result["overall"] = {s["name"]: {"home": s["home"], "away": s["away"]} for s in period["stats"]}

    if not result["overall"] and result["periods"]:
        last = result["periods"][-1]
        result["overall"] = {s["name"]: {"home": s["home"], "away": s["away"]} for s in last.get("stats", [])}

    return result


def filter_matches(
    matches: list[dict[str, Any]],
    *,
    live_only: bool = False,
    finished_only: bool = False,
    scheduled_only: bool = False,
) -> list[dict[str, Any]]:
    filtered = matches
    if live_only:
        filtered = [m for m in filtered if m.get("is_live")]
    if finished_only:
        filtered = [m for m in filtered if is_finished_tennis_match(m)]
    if scheduled_only:
        filtered = [m for m in filtered if m.get("is_scheduled")]
    return filtered


def build_finished_results(
    matches: list[dict[str, Any]],
    player_feeds: dict[str, dict[str, dict[str, str]]],
    extra_sources: dict[str, dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Enriquece partidos finalizados con marcador y resumen del resultado."""
    return [
        enrich_finished_match(match, player_feeds, extra_sources)
        for match in matches
    ]
