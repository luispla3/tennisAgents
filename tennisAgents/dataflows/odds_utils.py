"""Utilidades de cuotas usando el scraper de Betfair Sportsbook."""

from __future__ import annotations

import unicodedata
from datetime import datetime
from typing import Any, Optional

from tennisAgents.dataflows.betfair_scraper.scraper import (
    get_event_markets,
    get_live_matches,
    get_matches,
)
from tennisAgents.dataflows.betfair_scraper.client import BetfairError


def normalizar_nombre(nombre: str) -> str:
    nombre = unicodedata.normalize("NFD", nombre)
    nombre = "".join(c for c in nombre if unicodedata.category(c) != "Mn")
    return " ".join(nombre.lower().split())


def extraer_partes_nombre(nombre_completo: str) -> dict[str, Any]:
    nombre_completo = nombre_completo.strip()
    if "," in nombre_completo:
        partes_coma = nombre_completo.split(",", 1)
        apellido = partes_coma[0].strip()
        nombre = partes_coma[1].strip() if len(partes_coma) > 1 else ""
        todas_partes = ([apellido] + nombre.split()) if nombre else [apellido]
        return {"nombre": nombre, "apellido": apellido, "todas_partes": todas_partes}

    partes = nombre_completo.split()
    if not partes:
        return {"nombre": "", "apellido": "", "todas_partes": []}
    if len(partes) == 1:
        return {"nombre": "", "apellido": partes[0], "todas_partes": partes}
    return {"nombre": partes[0], "apellido": partes[-1], "todas_partes": partes}


def calcular_score_coincidencia(nombre_jugador: str, event_name: str) -> int:
    partes = extraer_partes_nombre(nombre_jugador)
    evento_norm = normalizar_nombre(event_name)
    score = 0

    for parte in partes["todas_partes"]:
        parte_norm = normalizar_nombre(parte)
        if len(parte_norm) < 2:
            continue
        if parte_norm in evento_norm:
            score += 10 if parte == partes["apellido"] else 5

    return score


def buscar_partido_por_jugador(nombre_jugador: str) -> Optional[dict[str, Any]]:
    """Busca un partido en Betfair por nombre de jugador."""
    print(f"[INFO] Buscando partido de '{nombre_jugador}' en Betfair...")

    try:
        matches = get_live_matches("tennis")
        if not matches:
            print("[INFO] Sin partidos en vivo; buscando en el cupón del día...")
            matches = get_matches("tennis", live_only=False)
    except BetfairError as exc:
        print(f"[ERROR] Betfair: {exc}")
        return None

    if not matches:
        print("[WARNING] No hay partidos disponibles en Betfair.")
        return None

    best_match = None
    best_score = 0
    for match in matches:
        label = f"{match.get('player1', '')} vs {match.get('player2', '')}"
        score = max(
            calcular_score_coincidencia(nombre_jugador, label),
            calcular_score_coincidencia(nombre_jugador, match.get("name", "")),
        )
        if score > best_score:
            best_score = score
            best_match = match

    if not best_match or best_score < 5:
        print(f"[WARNING] No se encontró coincidencia suficiente para '{nombre_jugador}'.")
        return None

    print(
        f"[SUCCESS] Partido encontrado: {best_match.get('player1')} vs "
        f"{best_match.get('player2')} (score={best_score})"
    )
    return best_match


def _adapt_markets(raw_markets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    adapted = []
    for market in raw_markets:
        runners = []
        for runner in market.get("runners", []):
            odds = runner.get("odds_decimal") or runner.get("odds")
            if odds is None:
                continue
            runners.append({"name": runner.get("name", ""), "odds": str(odds)})
        if runners:
            adapted.append({"market_name": market.get("name", "Mercado"), "runners": runners})
    return adapted


def fetch_betfair_odds(nombre_jugador: str) -> Optional[dict[str, Any]]:
    """Obtiene cuotas de Betfair para el partido de un jugador."""
    print("\n" + "=" * 80)
    print("SCRAPER DE BETFAIR - EXTRACTOR DE CUOTAS".center(80))
    print("=" * 80)

    match = buscar_partido_por_jugador(nombre_jugador)
    if not match:
        return None

    event_id = match.get("id")
    if not event_id:
        print("[ERROR] El partido encontrado no tiene ID de evento.")
        return None

    try:
        event_data = get_event_markets(int(event_id), sport="tennis")
    except (BetfairError, ValueError, TypeError) as exc:
        print(f"[ERROR] No se pudieron obtener mercados: {exc}")
        return None

    markets = _adapt_markets(event_data.get("markets", []))
    if not markets:
        print("[ERROR] No se encontraron mercados con cuotas.")
        return None

    event_name = match.get("name") or f"{match.get('player1')} vs {match.get('player2')}"
    result = {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "player_searched": nombre_jugador,
        "event_name": event_name,
        "event_id": event_id,
        "competition": match.get("competition", ""),
        "total_markets": len(markets),
        "total_selections": sum(len(m["runners"]) for m in markets),
        "markets": markets,
    }

    print(f"[SUCCESS] {len(markets)} mercados extraídos para evento {event_id}")
    return result
