"""Integración Betfair Exchange (MATCH_ODDS) en el colector."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

log = logging.getLogger("collector.betfair_exchange")

BOOK_SPORTSBOOK = "SPORTSBOOK"
BOOK_EXCHANGE = "EXCHANGE"

_BETFAIR_API_DIR = Path(__file__).resolve().parents[2] / "betfairAPI"


def _ensure_betfair_api_path() -> None:
    path = str(_BETFAIR_API_DIR.resolve())
    if path not in sys.path:
        sys.path.insert(0, path)


def tag_sportsbook_market(market: dict[str, Any] | None) -> dict[str, Any] | None:
    """Añade book=SPORTSBOOK a un mercado Sportsbook (y a sus runners)."""
    if not isinstance(market, dict):
        return market
    tagged = dict(market)
    tagged["book"] = BOOK_SPORTSBOOK
    runners = tagged.get("runners")
    if isinstance(runners, list):
        tagged_runners = []
        for runner in runners:
            if isinstance(runner, dict):
                r = dict(runner)
                r["book"] = BOOK_SPORTSBOOK
                tagged_runners.append(r)
            else:
                tagged_runners.append(runner)
        tagged["runners"] = tagged_runners
    return tagged


def tag_sportsbook_section(section: dict[str, Any]) -> dict[str, Any]:
    """Marca la sección betfair (Sportsbook) con identificador de libro."""
    out = dict(section)
    out["book"] = BOOK_SPORTSBOOK
    out["primary_market"] = tag_sportsbook_market(out.get("primary_market"))
    markets = out.get("markets")
    if isinstance(markets, list):
        out["markets"] = [
            tag_sportsbook_market(m) if isinstance(m, dict) else m for m in markets
        ]
    return out


def fetch_exchange_match_odds_by_event() -> tuple[dict[str, dict[str, Any]], str | None]:
    """
    Devuelve ({event_id: match_odds}, error_global_or_none).

    Si falla auth/API, el dict puede ir vacío y error describe el fallo.
    """
    _ensure_betfair_api_path()
    try:
        from exchange_tennis import (  # type: ignore
            BetfairExchangeError,
            fetch_inplay_tennis_match_odds,
        )
    except ImportError as exc:
        msg = f"No se pudo importar betfairAPI/exchange_tennis: {exc}"
        log.warning(msg)
        return {}, msg

    try:
        return fetch_inplay_tennis_match_odds(), None
    except BetfairExchangeError as exc:
        msg = str(exc)
        log.warning("Exchange MATCH_ODDS no disponible: %s", msg)
        return {}, msg
    except Exception as exc:
        msg = f"Error inesperado Exchange: {exc}"
        log.exception(msg)
        return {}, msg


def build_exchange_section(
    event_id: str | int,
    odds_by_event: dict[str, dict[str, Any]],
    *,
    fetch_error: str | None = None,
) -> dict[str, Any]:
    """Sección betfair_exchange para un snapshot."""
    eid = str(event_id)
    match_odds = odds_by_event.get(eid)
    if match_odds is not None:
        return {
            "book": BOOK_EXCHANGE,
            "match_odds": match_odds,
            "error": None,
        }
    return {
        "book": BOOK_EXCHANGE,
        "match_odds": None,
        "error": fetch_error
        or (f"Sin MATCH_ODDS Exchange in-play para event_id={eid}"),
    }
