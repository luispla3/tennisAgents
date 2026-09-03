"""Cliente Exchange: MATCH_ODDS de tenis en directo (library-friendly)."""

from __future__ import annotations

import logging
from typing import Any

import requests

from auth import keep_alive, load_session_token, login
from config import (
    APP_KEY,
    BETTING_URL,
    MAX_MARKET_BOOK_BATCH,
    TENNIS_EVENT_TYPE_ID,
)

log = logging.getLogger("betfairAPI.exchange_tennis")

BOOK_EXCHANGE = "EXCHANGE"


class BetfairExchangeError(RuntimeError):
    """Error de autenticación o API Exchange."""


def _headers(token: str) -> dict[str, str]:
    return {
        "X-Application": APP_KEY,
        "X-Authentication": token,
        "content-type": "application/json",
        "Accept": "application/json",
    }


def ensure_session_token(*, force_login: bool = False) -> str:
    """Devuelve un token válido o lanza BetfairExchangeError (sin sys.exit)."""
    if force_login:
        try:
            return login()
        except SystemExit as exc:
            raise BetfairExchangeError("Login Exchange fallido") from exc

    token = load_session_token()
    if token and keep_alive(token):
        return load_session_token() or token

    try:
        return login()
    except SystemExit as exc:
        raise BetfairExchangeError(
            "Login Exchange fallido; configura betfairAPI/.env "
            "(BETFAIR_USERNAME / BETFAIR_PASSWORD)"
        ) from exc


def _post(token: str, endpoint: str, payload: dict[str, Any]) -> Any:
    response = requests.post(
        f"{BETTING_URL}/{endpoint}/",
        headers=_headers(token),
        json=payload,
        timeout=30,
    )
    if response.status_code in (401, 403):
        raise BetfairExchangeError(
            f"Exchange auth error {response.status_code}: {response.text[:200]}"
        )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and data.get("faultcode"):
        raise BetfairExchangeError(str(data))
    return data


def _best_price(offers: list[dict[str, Any]] | None) -> float | None:
    if not offers:
        return None
    price = offers[0].get("price")
    return float(price) if price is not None else None


def _normalize_runner(
    *,
    selection_id: int | str | None,
    name: str,
    book_runner: dict[str, Any],
) -> dict[str, Any]:
    ex = book_runner.get("ex") or {}
    back = list(ex.get("availableToBack") or [])
    lay = list(ex.get("availableToLay") or [])
    last = book_runner.get("lastPriceTraded")
    return {
        "book": BOOK_EXCHANGE,
        "name": name,
        "selection_id": selection_id,
        "status": book_runner.get("status"),
        "best_back": _best_price(back),
        "best_lay": _best_price(lay),
        "last_price_traded": float(last) if last is not None else None,
        "available_to_back": back,
        "available_to_lay": lay,
    }


def _normalize_match_odds(
    catalogue: dict[str, Any],
    book: dict[str, Any] | None,
) -> dict[str, Any]:
    event = catalogue.get("event") or {}
    runner_names = {
        r.get("selectionId"): r.get("runnerName") or "?"
        for r in catalogue.get("runners") or []
    }
    book = book or {}
    runners = []
    for runner in book.get("runners") or []:
        sid = runner.get("selectionId")
        runners.append(
            _normalize_runner(
                selection_id=sid,
                name=str(runner_names.get(sid, "?")),
                book_runner=runner,
            )
        )
    return {
        "book": BOOK_EXCHANGE,
        "market_id": catalogue.get("marketId") or book.get("marketId"),
        "market_type": "MATCH_ODDS",
        "name": catalogue.get("marketName") or "Match Odds",
        "status": book.get("status") or catalogue.get("status"),
        "inplay": bool(book.get("inplay", catalogue.get("inPlay"))),
        "total_matched": book.get("totalMatched"),
        "event_id": str(event.get("id") or ""),
        "event_name": event.get("name"),
        "runners": runners,
    }


def fetch_inplay_tennis_match_odds(
    *,
    force_login: bool = False,
    max_results: int = 100,
) -> dict[str, dict[str, Any]]:
    """
    MATCH_ODDS Exchange de tenis in-play, indexados por event_id (str).

    Cada valor es un mercado normalizado con book=EXCHANGE.
    """
    token = ensure_session_token(force_login=force_login)
    try:
        markets = _post(
            token,
            "listMarketCatalogue",
            {
                "filter": {
                    "eventTypeIds": [TENNIS_EVENT_TYPE_ID],
                    "inPlayOnly": True,
                    "marketTypeCodes": ["MATCH_ODDS"],
                },
                "maxResults": str(max_results),
                "marketProjection": ["EVENT", "RUNNER_DESCRIPTION", "MARKET_START_TIME"],
            },
        )
    except BetfairExchangeError:
        # Token puede haber caducado a medias: un re-login y reintento.
        token = ensure_session_token(force_login=True)
        markets = _post(
            token,
            "listMarketCatalogue",
            {
                "filter": {
                    "eventTypeIds": [TENNIS_EVENT_TYPE_ID],
                    "inPlayOnly": True,
                    "marketTypeCodes": ["MATCH_ODDS"],
                },
                "maxResults": str(max_results),
                "marketProjection": ["EVENT", "RUNNER_DESCRIPTION", "MARKET_START_TIME"],
            },
        )

    if not isinstance(markets, list):
        raise BetfairExchangeError(f"Respuesta inesperada listMarketCatalogue: {markets!r}")

    market_ids = [m["marketId"] for m in markets if m.get("marketId")]
    books: list[dict[str, Any]] = []
    for i in range(0, len(market_ids), MAX_MARKET_BOOK_BATCH):
        chunk = market_ids[i : i + MAX_MARKET_BOOK_BATCH]
        chunk_books = _post(
            token,
            "listMarketBook",
            {
                "marketIds": chunk,
                "priceProjection": {"priceData": ["EX_BEST_OFFERS"]},
            },
        )
        if isinstance(chunk_books, list):
            books.extend(chunk_books)

    books_by_id = {b.get("marketId"): b for b in books if b.get("marketId")}
    by_event: dict[str, dict[str, Any]] = {}
    for catalogue in markets:
        event = catalogue.get("event") or {}
        event_id = str(event.get("id") or "")
        if not event_id:
            continue
        market_id = catalogue.get("marketId")
        by_event[event_id] = _normalize_match_odds(
            catalogue,
            books_by_id.get(market_id),
        )
    log.info(
        "Exchange MATCH_ODDS in-play: %s mercados / %s eventos",
        len(markets),
        len(by_event),
    )
    return by_event
