import json
import sys
from datetime import datetime, timezone

import requests

from auth import ensure_session, load_session_token
from config import ACCOUNT_URL, APP_KEY, BETTING_URL, KEEP_ALIVE_URL, LOGIN_URL

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def headers():
    return {
        "X-Application": APP_KEY,
        "X-Authentication": ensure_session(),
        "content-type": "application/json",
    }


def post(base, endpoint, payload=None):
    r = requests.post(f"{base}/{endpoint}/", headers=headers(), json=payload or {}, timeout=30)
    return r.status_code, r.json() if r.text else {}


def main():
    token = load_session_token()
    print("=" * 60)
    print("  ESTADO API BETFAIR")
    print("=" * 60)
    print(f"App Key: {APP_KEY}")
    print(f"Token:   {token[:10]}...{token[-6:] if len(token) > 16 else ''}")
    print()

    ka = requests.post(
        KEEP_ALIVE_URL,
        headers={"Accept": "application/json", "X-Application": APP_KEY, "X-Authentication": ensure_session()},
        timeout=30,
    ).json()
    print(f"Sesion keepAlive: {ka.get('status')}")

    code, funds = post(ACCOUNT_URL, "getAccountFunds")
    print(f"Cuenta (HTTP {code}): saldo={funds.get('availableToBetBalance')} EUR")

    code, types = post(BETTING_URL, "listMarketTypes", {"filter": {"eventTypeIds": ["2"]}})
    print(f"\nTipos mercado tenis (HTTP {code}):")
    for t in types:
        print(f"  - {t['marketType']}: {t['marketCount']}")

    code, inplay = post(
        BETTING_URL,
        "listMarketCatalogue",
        {
            "filter": {"eventTypeIds": ["2"], "inPlayOnly": True, "marketTypeCodes": ["MATCH_ODDS"]},
            "maxResults": "100",
            "marketProjection": ["EVENT"],
        },
    )
    print(f"\nPartidos tenis EN DIRECTO (Match Odds): {len(inplay)}")
    for m in inplay[:5]:
        print(f"  - {m['event']['name']} ({m['marketId']})")


if __name__ == "__main__":
    main()
