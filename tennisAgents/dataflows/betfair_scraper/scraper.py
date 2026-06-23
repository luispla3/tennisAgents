"""Funciones de alto nivel del scraper Betfair."""

from __future__ import annotations

import re
from typing import Any

from .client import BetfairClient, BetfairError
from .graphql import (
    GraphQLClient,
    event_view_urn,
    extract_navigation_tab_urns,
    find_navigation_tab,
    sport_view_urn,
)
from .parser import (
    build_event_markets,
    build_event_markets_from_gql,
    build_markets_from_gql,
    build_match_from_event_market_card,
    build_matches,
    build_matches_from_gql,
    iter_nodes_by_type,
    parse_catalog,
)

SPORT_ID_BY_KEY = {
    "tennis": 2,
    "tenis": 2,
    "football": 1,
    "futbol": 1,
    "basketball": 7522,
    "baloncesto": 7522,
}


def _merge_catalogs(catalogs: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, list] = {"data": {}}
    for catalog in catalogs:
        for key, items in catalog.get("data", {}).items():
            if not isinstance(items, list):
                continue
            bucket = merged["data"].setdefault(key, [])
            known = {item.get("urn") for item in bucket if isinstance(item, dict) and item.get("urn")}
            for item in items:
                if not isinstance(item, dict):
                    continue
                urn = item.get("urn")
                if urn and urn in known:
                    continue
                bucket.append(item)
                if urn:
                    known.add(urn)
    return merged


def _sport_id(sport: str) -> int | None:
    return SPORT_ID_BY_KEY.get(sport.lower().strip())


def _gql_client(client: BetfairClient) -> GraphQLClient:
    return GraphQLClient(client.app_key)


def _fetch_inplay_tab_payload(client: BetfairClient, sport: str) -> dict[str, Any]:
    sport_path = client.sport_path(sport)
    html, _catalog = client.fetch_page_bundle(sport_path)
    gql = _gql_client(client)
    tab_urns = extract_navigation_tab_urns(html, sport_path)
    if not tab_urns:
        raise BetfairError("No se encontraron pestañas de navegación en la página del deporte.")

    response = gql.fetch_cards(
        tab_urns,
        view_urn=sport_view_urn(sport_path),
        current_url=sport_path,
    )
    inplay_tab = find_navigation_tab(response.get("data", {}).get("Cards") or [], "En juego")
    if not inplay_tab:
        raise BetfairError("No se encontró la pestaña 'En juego' vía GraphQL.")
    return {"data": {"Cards": [inplay_tab]}}


def _event_pebble_urns(catalog: dict[str, Any], html: str = "") -> list[str]:
    urns: list[str] = []
    for tab in catalog.get("data", {}).get("NavigationTab", []):
        for item in tab.get("items", []):
            if item.get("typename") == "PebbleCardGroup" and item.get("urn"):
                urns.append(item["urn"])
    if urns:
        return urns
    if html:
        return sorted(
            set(
                re.findall(
                    r"ppb:tbd:cardgroup:pebble:marketTemplateEvent:[A-Za-z0-9_]+/e/\d+",
                    html,
                )
            )
        )
    return []


def _event_page_path(catalog: dict[str, Any], event_id: int) -> str:
    router = catalog.get("router") or {}
    current_url = router.get("currentUrl")
    if current_url:
        return current_url
    return f"event/e-{event_id}"


def _resolve_event_url(client: BetfairClient, gql: GraphQLClient, event_id: int) -> str | None:
    payload = gql.fetch_cards(
        [f"ppb:tbd:card:eventPrimaryMarket:{event_id}"],
        view_urn=event_view_urn(event_id),
        current_url=f"event/e-{event_id}",
    )
    for card in iter_nodes_by_type(payload, "EventMarketCard"):
        match = build_match_from_event_market_card(card)
        url = match.get("url") or ""
        if "/apuestas/" in url:
            return url.split("/apuestas/", 1)[-1]
        link = (card.get("eventViewLink") or {}).get("viewUrl")
        if link:
            return link
    return None


def _fetch_event_markets_gql(
    client: BetfairClient,
    gql: GraphQLClient,
    event_id: int,
) -> dict | None:
    event_path = _resolve_event_url(client, gql, event_id) or f"event/e-{event_id}"
    html, catalog = client.fetch_page_bundle(event_path)
    current_url = _event_page_path(catalog, event_id)
    pebble_urns = _event_pebble_urns(catalog, html)
    if not pebble_urns:
        return None

    view_urn = event_view_urn(event_id)
    referer = f"{client.base_url}/{current_url.lstrip('/')}"
    markets: list[dict] = []
    seen: set[str] = set()

    for index in range(0, len(pebble_urns), 5):
        batch = pebble_urns[index : index + 5]
        payload = gql.fetch_cards(
            batch,
            view_urn=view_urn,
            current_url=current_url,
            referer=referer,
        )
        for market in build_markets_from_gql(payload):
            market_id = market.get("market_id")
            if market_id and market_id in seen:
                continue
            if market_id:
                seen.add(market_id)
            markets.append(market)

    if not markets:
        return None

    primary_payload = gql.fetch_cards(
        [f"ppb:tbd:card:eventPrimaryMarket:{event_id}"],
        view_urn=view_urn,
        current_url=current_url,
        referer=referer,
    )
    result = build_event_markets_from_gql(primary_payload, event_id)
    result["markets"] = markets
    return result


def get_matches(sport: str = "tennis", live_only: bool = False) -> list[dict]:
    """Partidos del día (cupón 'Partidos de hoy')."""
    if live_only:
        return get_live_matches(sport)

    client = BetfairClient()
    catalogs = [client.fetch_catalog(client.discover_today_coupon(sport))]
    parsed = parse_catalog(_merge_catalogs(catalogs))
    return build_matches(parsed, sport_id=_sport_id(sport), live_only=False)


def get_live_matches(sport: str = "tennis") -> list[dict]:
    """Partidos en juego (pestaña 'En juego' vía GraphQL)."""
    payload = _fetch_inplay_tab_payload(BetfairClient(), sport)
    matches = build_matches_from_gql(payload, live_only=True)
    if not matches:
        client = BetfairClient()
        catalogs = [
            client.fetch_catalog(client.discover_inplay_path(sport)),
            client.fetch_catalog(client.discover_today_coupon(sport)),
        ]
        parsed = parse_catalog(_merge_catalogs(catalogs))
        matches = build_matches(parsed, sport_id=_sport_id(sport), live_only=True)
    return matches


def get_event_markets(event_id: int, sport: str = "tennis") -> dict:
    """Cuotas y mercados de un evento por su ID numérico."""
    client = BetfairClient()
    gql = _gql_client(client)

    try:
        result = _fetch_event_markets_gql(client, gql, event_id)
        if result:
            return result
    except BetfairError:
        pass

    catalogs = [
        client.fetch_catalog(client.discover_today_coupon(sport)),
        client.fetch_catalog(client.discover_inplay_path(sport)),
    ]
    parsed = parse_catalog(_merge_catalogs(catalogs))
    if str(event_id) not in parsed["events_by_id"] and event_id not in parsed["events_by_id"]:
        raise BetfairError(f"Evento {event_id} no encontrado.")

    event_url = parsed["event_urls"].get(event_id)
    if event_url:
        try:
            catalogs.append(client.fetch_catalog(event_url))
            parsed = parse_catalog(_merge_catalogs(catalogs))
        except BetfairError:
            pass

    try:
        return build_event_markets(parsed, event_id)
    except KeyError as exc:
        raise BetfairError(str(exc)) from exc
