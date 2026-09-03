import argparse
import sys
from collections import defaultdict

import requests

from auth import ensure_session, login
from config import APP_KEY, BETTING_URL, MAX_MARKET_BOOK_BATCH, TENNIS_EVENT_TYPE_ID

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def get_headers():
    return {
        "X-Application": APP_KEY,
        "X-Authentication": ensure_session(),
        "content-type": "application/json",
    }


def betting_post(endpoint, payload):
    response = requests.post(
        f"{BETTING_URL}/{endpoint}/",
        headers=get_headers(),
        json=payload,
        timeout=30,
    )
    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
        sys.exit(1)
    return response.json()


def format_price_ladder(offers):
    if not offers:
        return "Ninguna"
    return ", ".join([f"{offer['price']}({offer['size']}€)" for offer in offers])


def get_tennis_markets(event_id=None, in_play_only=False):
    market_filter = {"eventTypeIds": [TENNIS_EVENT_TYPE_ID]}
    if event_id:
        market_filter["eventIds"] = [event_id]
    if in_play_only:
        market_filter["inPlayOnly"] = True
        market_filter["marketTypeCodes"] = ["MATCH_ODDS"]

    return betting_post(
        "listMarketCatalogue",
        {
            "filter": market_filter,
            "maxResults": "1000",
            "marketProjection": [
                "COMPETITION",
                "EVENT",
                "MARKET_START_TIME",
                "RUNNER_DESCRIPTION",
            ],
        },
    )


def get_market_books(market_ids):
    books = []
    for i in range(0, len(market_ids), MAX_MARKET_BOOK_BATCH):
        batch = market_ids[i : i + MAX_MARKET_BOOK_BATCH]
        books.extend(
            betting_post(
                "listMarketBook",
                {
                    "marketIds": batch,
                    "priceProjection": {
                        "priceData": ["EX_ALL_OFFERS"],
                        "virtualise": True,
                    },
                },
            )
        )
    return books


def format_runner_odds(runner, runner_names):
    name = runner_names.get(runner["selectionId"], str(runner["selectionId"]))
    back_ladder = runner.get("ex", {}).get("availableToBack", [])
    lay_ladder = runner.get("ex", {}).get("availableToLay", [])
    last = runner.get("lastPriceTraded", "N/A")
    backs_str = format_price_ladder(back_ladder)
    lays_str = format_price_ladder(lay_ladder)
    return f"  - {name}:\n    Backs: [{backs_str}]\n    Lays:  [{lays_str}]\n    Ultimo: {last}"


def print_market_odds(market, book):
    runner_names = {
        runner["selectionId"]: runner["runnerName"] for runner in market["runners"]
    }

    inplay = book.get("inplay", False)
    print(f"Mercado: {market['marketName']} (id: {market['marketId']})")
    if inplay:
        print("  (EN DIRECTO)")
    if book.get("isMarketDataDelayed"):
        print("  (datos retrasados)")
    elif not inplay:
        print("  (datos en vivo)")

    for runner in book.get("runners", []):
        print(format_runner_odds(runner, runner_names))
    print()


def list_tennis_matches(in_play_only=False):
    markets = get_tennis_markets(in_play_only=in_play_only)
    by_event = defaultdict(list)
    for market in markets:
        by_event[market["event"]["id"]].append(market)

    label = "en directo" if in_play_only else "disponibles"
    print(f"Partidos de tenis {label} ({len(by_event)}):\n")
    for event_id in sorted(
        by_event,
        key=lambda eid: by_event[eid][0]["event"]["openDate"],
    ):
        event = by_event[event_id][0]["event"]
        event_markets = sorted(by_event[event_id], key=lambda m: m["marketName"])
        print(
            f"  [{event_id}] {event['name']} "
            f"- {event['openDate']} UTC "
            f"({len(event_markets)} mercado(s))"
        )
        for market in event_markets:
            print(f"      * {market['marketName']} (mercado: {market['marketId']})")
        print()


def show_event_odds(event_id):
    markets = get_tennis_markets(event_id=event_id)
    if not markets:
        print(f"No se encontraron mercados para el evento {event_id}.")
        sys.exit(1)

    event_name = markets[0]["event"]["name"]
    print(f"Cuotas para: {event_name} (id: {event_id})\n")
    print(f"Mercados encontrados: {len(markets)}\n")

    market_ids = [market["marketId"] for market in markets]
    books_by_id = {book["marketId"]: book for book in get_market_books(market_ids)}

    for market in sorted(markets, key=lambda m: m["marketName"]):
        print_market_odds(market, books_by_id.get(market["marketId"], {}))


def main():
    parser = argparse.ArgumentParser(description="Consultas de tenis en Betfair API")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-login", action="store_true", help="Inicia sesion y guarda token")
    group.add_argument("-list", action="store_true", help="Lista partidos de tenis")
    group.add_argument(
        "-live",
        action="store_true",
        help="Lista solo partidos en directo (Match Odds)",
    )
    group.add_argument(
        "-id",
        metavar="ID",
        help="Cuotas de todos los mercados de un partido",
    )
    args = parser.parse_args()

    if args.login:
        login()
    elif args.live:
        list_tennis_matches(in_play_only=True)
    elif args.list:
        list_tennis_matches()
    else:
        show_event_odds(args.id)


if __name__ == "__main__":
    main()
