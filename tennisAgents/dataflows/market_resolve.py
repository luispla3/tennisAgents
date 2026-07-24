"""Resolución robusta de mercados/selecciones Betfair frente a nombres del LLM."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

_MARKET_ALIASES: dict[str, str] = {
    "match_winner": "MATCH_ODDS",
    "match winner": "MATCH_ODDS",
    "match odds": "MATCH_ODDS",
    "cuotas de partido": "MATCH_ODDS",
    "ganador del partido": "MATCH_ODDS",
    "ganador partido": "MATCH_ODDS",
    "set betting": "SET_BETTING",
    "apuestas a sets": "SET_BETTING",
    "set betting standard": "SET_BETTING_STANDARD",
}


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().replace(",", ".")
    text = re.sub(r"[^a-z0-9./]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def set_is_complete(games_a: int, games_b: int) -> bool:
    """True si el marcador de un set ya es terminal en tenis."""
    high, low = max(games_a, games_b), min(games_a, games_b)
    if high < 6:
        return False
    if high == 6:
        return low <= 4
    if high == 7 and low == 6:
        return True
    return high - low >= 2


def parse_sets_detail(score: str | None) -> list[dict[str, int]]:
    if not score:
        return []
    sets: list[dict[str, int]] = []
    for part in str(score).split():
        if "-" not in part:
            continue
        left, _, right = part.partition("-")
        try:
            sets.append({"player1": int(left), "player2": int(right)})
        except ValueError:
            continue
    return sets


def derive_sets_won(sets_detail: list[dict[str, int]] | None) -> dict[str, int]:
    p1 = p2 = 0
    for item in sets_detail or []:
        a = int(item.get("player1") or 0)
        b = int(item.get("player2") or 0)
        if not set_is_complete(a, b):
            continue
        if a > b:
            p1 += 1
        elif b > a:
            p2 += 1
    return {"player1": p1, "player2": p2}


def build_game_winners_from_scores(
    scores: list[str],
) -> dict[tuple[int, int], str]:
    """
    Infieres ganadores de juego por la progresión del marcador entre snapshots.

    Clave: (set_number_1based, game_number_1based) -> 'player1'|'player2'
    """
    winners: dict[tuple[int, int], str] = {}
    previous: list[dict[str, int]] = []
    for score in scores:
        current = parse_sets_detail(score)
        max_sets = max(len(previous), len(current))
        for set_idx in range(max_sets):
            prev = (
                previous[set_idx]
                if set_idx < len(previous)
                else {"player1": 0, "player2": 0}
            )
            curr = (
                current[set_idx]
                if set_idx < len(current)
                else {"player1": 0, "player2": 0}
            )
            prev_total = int(prev["player1"]) + int(prev["player2"])
            # Reinicios espurios (0-0 tras un marcador avanzado) se ignoran.
            if (
                int(curr["player1"]) + int(curr["player2"]) < prev_total
                and int(curr["player1"]) == 0
                and int(curr["player2"]) == 0
            ):
                continue
            delta_p1 = int(curr["player1"]) - int(prev["player1"])
            delta_p2 = int(curr["player2"]) - int(prev["player2"])
            set_number = set_idx + 1
            if delta_p1 > 0 and delta_p2 == 0:
                for step in range(delta_p1):
                    game_number = prev_total + step + 1
                    winners.setdefault((set_number, game_number), "player1")
            elif delta_p2 > 0 and delta_p1 == 0:
                for step in range(delta_p2):
                    game_number = prev_total + step + 1
                    winners.setdefault((set_number, game_number), "player2")
        if current:
            previous = current
    return winners


def _alias_market_type(wanted: str) -> str | None:
    normalized = normalize_text(wanted)
    if not normalized:
        return None
    compact = normalized.replace(" ", "_")
    if compact.upper() == compact.replace(" ", "_"):
        # Ya parece un market_type.
        pass
    aliased = _MARKET_ALIASES.get(normalized) or _MARKET_ALIASES.get(
        normalized.replace(" ", "_")
    )
    if aliased:
        return aliased

    correct = re.search(
        r"set\s*([123]).*(resultado|marcador|correct)",
        normalized,
    )
    if correct:
        ordinal = {"1": "1ST", "2": "2ND", "3": "3RD"}[correct.group(1)]
        return f"CORRECT_SCORE_{ordinal}_SET"

    game = re.search(r"set\s*([123]).*juego\s*(\d+).*ganador", normalized)
    if game:
        return f"SET_{game.group(1)}_GAME_{int(game.group(2))}_WINNER"

    total = re.search(
        r"set\s*([123]).*total.*juegos.*(?:mas|menos|over|under).*?(\d+(?:\.\d+)?)",
        normalized,
    )
    if total:
        return f"SET_{total.group(1)}_TOTAL_GAMES_OVER/UNDER_{total.group(2)}"

    winner = re.search(r"set\s*([123]).*ganador$", normalized)
    if winner and "juego" not in normalized:
        set_n = winner.group(1)
        return f"SET_0{set_n}_WINNER" if set_n == "1" else f"SET_{set_n}_WINNER"

    return None


def _market_identifiers(market: dict[str, Any]) -> set[str]:
    values = {
        normalize_text(market.get("market_type")),
        normalize_text(market.get("market_id")),
        normalize_text(market.get("name")),
        str(market.get("market_type") or "").strip().casefold(),
        str(market.get("market_id") or "").strip().casefold(),
        str(market.get("name") or "").strip().casefold(),
    }
    market_type = str(market.get("market_type") or "").strip().upper()
    if market_type:
        values.add(market_type.casefold())
        values.add(normalize_text(market_type))
    return {value for value in values if value}


def _runner_matches(runner: dict[str, Any], wanted_option: str) -> bool:
    name = str(runner.get("name") or "")
    if not wanted_option:
        return False
    if name.strip().casefold() == wanted_option.strip().casefold():
        return True
    left = normalize_text(name)
    right = normalize_text(wanted_option)
    if not left or not right:
        return False
    if left == right:
        return True
    # "Gonzalo Bueno Si" vs "Gonzalo Bueno"
    if left.startswith(right + " ") or right.startswith(left + " "):
        return True
    # "Menos de 7.5" vs "Menos de 7,5"
    if left.replace(" ", "") == right.replace(" ", ""):
        return True
    return False


def resolve_market_selection(
    markets: list[dict[str, Any]],
    market_query: str,
    option: str,
    *,
    market_id: str | None = None,
    selection_id: Any = None,
    primary_market: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    pool = list(markets or [])
    if primary_market and not any(
        market.get("market_id") == primary_market.get("market_id") for market in pool
    ):
        pool.insert(0, primary_market)

    wanted_market = str(market_query or "").strip()
    wanted_option = str(option or "").strip()
    aliased = _alias_market_type(wanted_market)
    wanted_keys = {
        wanted_market.casefold(),
        normalize_text(wanted_market),
    }
    if aliased:
        wanted_keys.add(aliased.casefold())
        wanted_keys.add(normalize_text(aliased))

    candidates: list[dict[str, Any]] = []
    for market in pool:
        if market_id:
            if str(market.get("market_id") or "") == str(market_id):
                candidates.append(market)
            continue
        identifiers = _market_identifiers(market)
        if wanted_keys & identifiers:
            candidates.append(market)
            continue
        # Coincidencia parcial por nombre visible cuando el LLM copia el label.
        name_norm = normalize_text(market.get("name"))
        query_norm = normalize_text(wanted_market)
        if name_norm and query_norm and (
            name_norm == query_norm
            or (len(query_norm) >= 12 and query_norm in name_norm)
            or (len(name_norm) >= 12 and name_norm in query_norm)
        ):
            candidates.append(market)

    if not candidates and aliased:
        for market in pool:
            if str(market.get("market_type") or "").strip().upper() == aliased:
                candidates.append(market)

    # SET_01_WINNER vs SET_1_WINNER
    if not candidates and aliased and "WINNER" in aliased and "GAME" not in aliased:
        alt = aliased.replace("SET_01_", "SET_1_").replace("SET_1_", "SET_01_")
        for market in pool:
            if str(market.get("market_type") or "").strip().upper() == alt:
                candidates.append(market)

    for market in candidates:
        for runner in market.get("runners") or []:
            if selection_id is not None:
                if str(runner.get("selection_id")) == str(selection_id):
                    return market, runner
                continue
            if _runner_matches(runner, wanted_option):
                return market, runner
    return None, None
