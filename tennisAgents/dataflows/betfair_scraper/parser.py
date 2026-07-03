"""Parser del catálogo precargado de Betfair Sportsbook."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

TENNIS_SPORT_URN = "ppb:eventType:2"


def _index_by_key(items: list[dict], key: str) -> dict[str, dict]:
    return {str(item[key]): item for item in items if key in item}


def _index_by_urn(items: list[dict]) -> dict[str, dict]:
    return {item["urn"]: item for item in items if item.get("urn")}


def _event_id_from_urn(urn: str) -> Optional[int]:
    if not urn:
        return None
    if urn.startswith("ppb:event:"):
        try:
            return int(urn.split(":")[-1])
        except ValueError:
            return None
    return None


def _sport_id_from_urn(urn: str) -> Optional[int]:
    if urn and urn.startswith("ppb:eventType:"):
        try:
            return int(urn.split(":")[-1])
        except ValueError:
            return None
    return None


def _format_open_date(iso_date: Optional[str]) -> Optional[str]:
    if not iso_date:
        return None
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return iso_date


def _runner_odds(
    market: dict,
    runner_data: dict[str, dict],
) -> list[dict[str, Any]]:
    runners = []
    for runner in market.get("runners", []):
        urn = runner.get("urn", "")
        live = runner_data.get(urn, {})
        odds = live.get("odds") or {}
        decimal = odds.get("decimal")
        fractional = odds.get("fractional")
        frac_str = None
        if fractional:
            frac_str = f"{fractional.get('numerator')}/{fractional.get('denominator')}"
        runners.append(
            {
                "name": runner.get("name"),
                "selection_id": runner.get("selectionId"),
                "result_type": runner.get("resultType"),
                "status": live.get("status", runner.get("status")),
                "odds_decimal": decimal,
                "odds_fractional": frac_str,
            }
        )
    return runners


def parse_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    """Normaliza entidades del catálogo precargado."""
    data = catalog.get("data", {})

    events = _index_by_urn(data.get("SportsEvent", []))
    events_by_id = _index_by_key(
        [{**e, "eventId": e.get("eventId")} for e in data.get("SportsEvent", []) if e.get("eventId")],
        "eventId",
    )
    markets = _index_by_urn(data.get("SportsbookMarket", []))
    markets_by_id = _index_by_key(
        [{**m, "marketId": m.get("marketId")} for m in data.get("SportsbookMarket", []) if m.get("marketId")],
        "marketId",
    )
    runner_data = _index_by_urn(data.get("SportsbookRunnerLiveData", []))
    competitions = _index_by_urn(data.get("Competition", []))
    sports = _index_by_urn(data.get("Sport", []))
    tennis_matches = _index_by_urn(data.get("TennisMatch", []))
    event_cards = data.get("EventMarketCard", [])

    event_urls: dict[int, str] = {}
    for card in event_cards:
        eid = _event_id_from_urn(card.get("sportevent", ""))
        link = card.get("eventViewLink", {}).get("viewUrl")
        if eid and link:
            event_urls[eid] = link

    market_groups: dict[int, list[dict]] = {}
    for market in data.get("SportsbookMarket", []):
        event_urn = market.get("hierarchy", {}).get("sportevent", "")
        eid = _event_id_from_urn(event_urn)
        if not eid:
            continue
        market_groups.setdefault(eid, []).append(market)

    pebble_groups: dict[int, list[str]] = {}
    for tab in data.get("NavigationTab", []):
        for item in tab.get("items", []):
            if item.get("typename") != "PebbleCardGroup":
                continue
            urn = item.get("urn", "")
            match = urn.split("/e/")
            if len(match) != 2:
                continue
            try:
                eid = int(match[1])
            except ValueError:
                continue
            title = None
            for group in data.get("PebbleCardGroup", []):
                if group.get("urn") == urn:
                    title = group.get("title", {}).get("translated")
                    break
            pebble_groups.setdefault(eid, []).append(title or urn)

    return {
        "events": events,
        "events_by_id": events_by_id,
        "markets": markets,
        "markets_by_id": markets_by_id,
        "runner_data": runner_data,
        "competitions": competitions,
        "sports": sports,
        "tennis_matches": tennis_matches,
        "event_urls": event_urls,
        "market_groups": market_groups,
        "pebble_groups": pebble_groups,
    }


def _market_sport_id(market: dict, parsed: dict[str, Any]) -> Optional[int]:
    sport_urn = market.get("sport")
    sport_id = _sport_id_from_urn(sport_urn or "")
    if sport_id is not None:
        return sport_id
    comp_urn = market.get("hierarchy", {}).get("competition")
    comp = parsed["competitions"].get(comp_urn or "", {})
    return comp.get("sport", {}).get("sportId")


def _build_match(
    event: dict,
    parsed: dict[str, Any],
    primary_market: Optional[dict] = None,
) -> dict[str, Any]:
    eid = event.get("eventId")
    tennis = None
    for fixture in parsed["tennis_matches"].values():
        if _event_id_from_urn(fixture.get("sportevent", "")) == eid:
            tennis = fixture
            break

    player1 = player2 = None
    if tennis:
        names = tennis.get("runnerNames", {})
        player1 = names.get("home")
        player2 = names.get("away")
    elif event.get("name") and " - " in event["name"]:
        parts = event["name"].split(" - ", 1)
        player1, player2 = parts[0].strip(), parts[1].strip()

    market = primary_market
    if not market and eid in parsed["market_groups"]:
        for candidate in parsed["market_groups"][eid]:
            if candidate.get("marketType") == "MATCH_ODDS":
                market = candidate
                break
        if not market:
            market = parsed["market_groups"][eid][0]

    odds = []
    market_summary = None
    is_live = False
    status = "Programado"

    if market:
        is_live = bool(market.get("inplay"))
        market_status = market.get("status", "")
        if is_live:
            status = "En juego"
        elif market_status == "OPEN":
            status = "Abierto"
        elif market_status == "SUSPENDED":
            status = "Suspendido"
        elif market_status == "CLOSED":
            status = "Cerrado"

        odds = _runner_odds(market, parsed["runner_data"])
        market_summary = {
            "market_id": market.get("marketId"),
            "name": market.get("name"),
            "market_type": market.get("marketType"),
            "status": market.get("status"),
            "inplay": is_live,
            "runners": odds,
        }

    if tennis:
        match_status = tennis.get("status", {}).get("status")
        if match_status == "IN_RUNNING":
            status = "En juego"
            is_live = True
        elif match_status == "PRE_MATCH":
            status = "Programado"
        elif match_status:
            status = match_status.replace("_", " ").title()

    comp_urn = event.get("competition")
    competition = parsed["competitions"].get(comp_urn or {}, {})

    event_url = parsed["event_urls"].get(eid)
    if not event_url and eid:
        event_url = f"event/e-{eid}"

    return {
        "id": eid,
        "name": event.get("name"),
        "player1": player1,
        "player2": player2,
        "start_time": _format_open_date(event.get("openDate")),
        "status": status,
        "is_live": is_live,
        "competition": competition.get("name"),
        "surface": tennis.get("surface") if tennis else None,
        "primary_market": market_summary,
        "url": f"https://www.betfair.es/apuestas/{event_url}" if event_url else None,
    }


def build_matches(
    parsed: dict[str, Any],
    *,
    sport_id: Optional[int] = 2,
    live_only: bool = False,
) -> list[dict[str, Any]]:
    """Construye lista de partidos a partir del catálogo parseado."""
    matches: list[dict[str, Any]] = []
    seen: set[int] = set()

    for event in parsed["events_by_id"].values():
        eid = event.get("eventId")
        if not eid or eid in seen:
            continue

        markets = parsed["market_groups"].get(eid, [])
        if sport_id is not None:
            sport_ids = {_market_sport_id(m, parsed) for m in markets}
            sport_ids.discard(None)
            if sport_ids and sport_id not in sport_ids:
                continue

        primary = next((m for m in markets if m.get("marketType") == "MATCH_ODDS"), None)
        match = _build_match(event, parsed, primary_market=primary)

        if live_only and not match.get("is_live"):
            continue

        matches.append(match)
        seen.add(eid)

    matches.sort(key=lambda m: m.get("start_time") or "")
    return matches


def build_event_markets(parsed: dict[str, Any], event_id: int) -> dict[str, Any]:
    """Devuelve todos los mercados conocidos de un evento en el catálogo."""
    event = parsed["events_by_id"].get(str(event_id)) or parsed["events_by_id"].get(event_id)
    if not event:
        raise KeyError(f"Evento {event_id} no encontrado en el catálogo")

    markets_out = []
    for market in parsed["market_groups"].get(event_id, []):
        markets_out.append(
            {
                "market_id": market.get("marketId"),
                "name": market.get("name"),
                "market_type": market.get("marketType"),
                "status": market.get("status"),
                "inplay": market.get("inplay"),
                "betting_type": market.get("bettingType"),
                "runners": _runner_odds(market, parsed["runner_data"]),
            }
        )

    available_groups = parsed["pebble_groups"].get(event_id, [])

    match = _build_match(
        event,
        parsed,
        primary_market=next((m for m in parsed["market_groups"].get(event_id, []) if m.get("marketType") == "MATCH_ODDS"), None),
    )

    return {
        "event": match,
        "markets": markets_out,
        "available_market_groups": available_groups,
    }


def _market_id_from_urn(urn: Optional[str]) -> Optional[str]:
    if not urn or not urn.startswith("ppb:sbkMarket:"):
        return None
    return urn.split(":", 2)[-1]


def _format_fractional(fractional: Optional[dict]) -> Optional[str]:
    if not fractional:
        return None
    num = fractional.get("numerator")
    den = fractional.get("denominator")
    if num is None or den is None:
        return None
    return f"{num}/{den}"


def _gql_runner_odds(market: dict[str, Any]) -> list[dict[str, Any]]:
    live_runners = (market.get("liveData") or {}).get("runners") or []
    odds_by_selection = {
        rd.get("selectionId"): rd
        for rd in live_runners
        if isinstance(rd, dict) and rd.get("selectionId") is not None
    }
    runners_out = []
    for runner in market.get("runners") or []:
        if not isinstance(runner, dict):
            continue
        selection_id = runner.get("selectionId")
        live = odds_by_selection.get(selection_id, {})
        odds = live.get("odds") or live.get("displayOdds") or {}
        decimal = odds.get("decimal")
        if decimal is None:
            display = live.get("displayOdds") or {}
            decimal = display.get("decimal")
        runners_out.append(
            {
                "name": runner.get("name"),
                "selection_id": selection_id,
                "result_type": runner.get("resultType"),
                "status": live.get("runnerStatus", runner.get("status")),
                "odds_decimal": decimal,
                "odds_fractional": _format_fractional(odds.get("fractional")),
            }
        )
    return runners_out


def _gql_market_summary(market: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not market:
        return None
    live_data = market.get("liveData") or {}
    return {
        "market_id": _market_id_from_urn(market.get("urn")),
        "name": market.get("name"),
        "market_type": market.get("marketType"),
        "status": live_data.get("sportsbookMarketStatus") or market.get("status"),
        "inplay": live_data.get("inplay"),
        "runners": _gql_runner_odds(market),
    }


def _gql_market_detail(market: dict[str, Any]) -> dict[str, Any]:
    live_data = market.get("liveData") or {}
    summary = _gql_market_summary(market) or {}
    return {
        **summary,
        "betting_type": market.get("bettingType"),
        "inplay": live_data.get("inplay"),
        "status": live_data.get("sportsbookMarketStatus") or market.get("status"),
        "runners": _gql_runner_odds(market),
    }


def iter_nodes_by_type(node: Any, typename: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("__typename") == typename:
                found.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(node)
    return found


def extract_tennis_live_score(fixture: dict[str, Any] | None) -> dict[str, Any] | None:
    """Marcador en vivo desde el fixture GraphQL de Betfair (tenis)."""
    if not fixture or fixture.get("__typename") != "TennisMatch":
        return None

    current_set = fixture.get("currentSet") or {}
    current_game = current_set.get("currentGame") or {}

    serving = None
    team_serving = current_game.get("teamServing")
    if team_serving == "HOME":
        serving = "player1"
    elif team_serving == "AWAY":
        serving = "player2"

    team_a_sets = fixture.get("teamAScore")
    team_b_sets = fixture.get("teamBScore")
    set_a = current_set.get("teamAScore")
    set_b = current_set.get("teamBScore")

    live: dict[str, Any] = {}
    if team_a_sets is not None and team_b_sets is not None:
        live["sets_won"] = {"player1": int(team_a_sets), "player2": int(team_b_sets)}
    if set_a is not None and set_b is not None:
        live["current_set"] = {"player1": int(set_a), "player2": int(set_b)}
    if current_game:
        live["current_game"] = {
            "player1": str(current_game.get("teamAScore", "")),
            "player2": str(current_game.get("teamBScore", "")),
        }
    if serving:
        live["serving"] = serving
    return live or None


def build_match_from_event_market_card(card: dict[str, Any]) -> dict[str, Any]:
    event = card.get("sportevent") or {}
    fixture = card.get("fixture") or {}
    names = fixture.get("runnerNames") or {}
    player1 = names.get("home")
    player2 = names.get("away")

    sportsbook = (card.get("displayRunners") or {}).get("sportsbook") or {}
    market = sportsbook.get("market") or {}
    market_summary = _gql_market_summary(market)

    status = "Programado"
    is_live = bool((market.get("liveData") or {}).get("inplay"))
    match_status = (fixture.get("status") or {}).get("status")
    if match_status == "IN_RUNNING":
        status = "En juego"
        is_live = True
    elif match_status:
        status = str(match_status).replace("_", " ").title()

    competition = (event.get("competition") or {}).get("name")
    event_url = (card.get("eventViewLink") or {}).get("viewUrl")
    eid = event.get("eventId")

    return {
        "id": eid,
        "name": event.get("name"),
        "player1": player1,
        "player2": player2,
        "start_time": _format_open_date(event.get("openDate")),
        "status": status,
        "is_live": is_live,
        "competition": competition,
        "surface": fixture.get("surface"),
        "primary_market": market_summary,
        "live_score": extract_tennis_live_score(fixture),
        "url": f"https://www.betfair.es/apuestas/{event_url}" if event_url else None,
    }


def build_matches_from_gql(
    payload: dict[str, Any],
    *,
    live_only: bool = False,
) -> list[dict[str, Any]]:
    """Construye partidos a partir de una respuesta GraphQL Cards."""
    cards = payload.get("data", {}).get("Cards") or []
    matches: list[dict[str, Any]] = []
    seen: set[int] = set()

    for root in cards:
        if not root:
            continue
        for card in iter_nodes_by_type(root, "EventMarketCard"):
            match = build_match_from_event_market_card(card)
            eid = match.get("id")
            if not eid or eid in seen:
                continue
            if live_only and not match.get("is_live"):
                continue
            matches.append(match)
            seen.add(eid)

    matches.sort(key=lambda m: m.get("start_time") or "")
    return matches


def build_markets_from_gql(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrae mercados SportsbookMarket de una respuesta GraphQL."""
    markets: list[dict[str, Any]] = []
    seen: set[str] = set()

    for card in payload.get("data", {}).get("Cards") or []:
        if not card:
            continue
        for market in iter_nodes_by_type(card, "SportsbookMarket"):
            urn = market.get("urn")
            if not urn or urn in seen:
                continue
            seen.add(urn)
            markets.append(_gql_market_detail(market))

    return markets


def build_event_markets_from_gql(
    payload: dict[str, Any],
    event_id: int,
) -> dict[str, Any]:
    """Construye respuesta de mercados de un evento desde GraphQL."""
    event_card = None
    cards = payload.get("data", {}).get("Cards") or []
    for root in cards:
        if not root:
            continue
        for card in iter_nodes_by_type(root, "EventMarketCard"):
            event = card.get("sportevent") or {}
            if event.get("eventId") == event_id:
                event_card = card
                break
        if event_card:
            break

    markets = build_markets_from_gql(payload)
    if event_card:
        event_match = build_match_from_event_market_card(event_card)
    elif markets:
        first = next(
            (
                m
                for m in iter_nodes_by_type(payload, "SportsbookMarket")
                if ((m.get("hierarchy") or {}).get("sportevent") or {}).get("eventId") == event_id
            ),
            None,
        )
        if first:
            ev = (first.get("hierarchy") or {}).get("sportevent") or {}
            event_match = {
                "id": event_id,
                "name": ev.get("name"),
                "player1": None,
                "player2": None,
                "start_time": _format_open_date(ev.get("openDate")),
                "status": "Programado",
                "is_live": bool((first.get("liveData") or {}).get("inplay")),
                "competition": ((ev.get("competition") or {}).get("name")),
                "surface": None,
                "primary_market": _gql_market_summary(first),
                "url": f"https://www.betfair.es/apuestas/event/e-{event_id}",
            }
        else:
            raise KeyError(f"Evento {event_id} no encontrado en GraphQL")
    else:
        raise KeyError(f"Evento {event_id} no encontrado en GraphQL")

    primary = next((m for m in markets if m.get("market_type") == "MATCH_ODDS"), None)
    if primary and event_match.get("primary_market") is None:
        event_match["primary_market"] = primary

    return {
        "event": event_match,
        "markets": markets,
    }
