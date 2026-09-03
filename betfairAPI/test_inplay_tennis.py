"""Prueba Match Odds en partidos de tenis en directo."""
import json
import sys
from pathlib import Path

from exchange_tennis import fetch_inplay_tennis_match_odds

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUT_JSON = Path(__file__).parent / "inplay_tennis_test_output.json"


def main():
    by_event = fetch_inplay_tennis_match_odds()
    results = list(by_event.values())
    summary = {
        "inplay_markets": len(results),
        "inplay_events": len(by_event),
        "match_odds_works": any(
            r.get("inplay")
            and any(
                (o.get("best_back") is not None) or (o.get("best_lay") is not None)
                for o in r.get("runners") or []
            )
            for r in results
        ),
        "matches": [
            {
                "event_id": r.get("event_id"),
                "event_name": r.get("event_name"),
                "market_id": r.get("market_id"),
                "inplay": r.get("inplay"),
                "status": r.get("status"),
                "book": r.get("book"),
                "odds": [
                    {
                        "name": o.get("name"),
                        "back": o.get("best_back"),
                        "lay": o.get("best_lay"),
                        "last": o.get("last_price_traded"),
                    }
                    for o in r.get("runners") or []
                ],
            }
            for r in results
        ],
    }

    OUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Partidos en directo: {summary['inplay_events']}")
    print(f"MATCH_ODDS operativo: {'SI' if summary['match_odds_works'] else 'NO/PARCIAL'}")
    print()
    for r in summary["matches"][:8]:
        print(f"[{r['event_id']}] {r['event_name']}")
        print(
            f"  book={r['book']} inplay={r['inplay']} "
            f"status={r['status']} market={r['market_id']}"
        )
        for o in r["odds"]:
            print(f"  - {o['name']}: Back={o['back']} Lay={o['lay']} Ultimo={o['last']}")
        print()


if __name__ == "__main__":
    main()
