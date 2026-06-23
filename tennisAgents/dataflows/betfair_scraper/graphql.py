"""Cliente GraphQL de Betfair Sportsbook (BFF)."""

from __future__ import annotations

import json
import re
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .client import BetfairError, DEFAULT_USER_AGENT

GQL_ENDPOINT = "https://apitbd.betfair.es/api/tbd/bff-gql/v11/"
CARD_DOCUMENT_ID = "Card#e790c877715333c5873badebe1846e23"

DEFAULT_EXPERIMENTS = [
    {"id": "uki_safety_rti_10k_stakes", "variant": "display"},
]

DEFAULT_PREFERENCES = {
    "userProducts": ["SPORTSBOOK", "GAMES"],
    "favoriteSports": [],
}


class GraphQLClient:
    """Consulta la API BFF de Betfair con persisted queries (documentId)."""

    def __init__(self, app_key: str, locale: str = "es") -> None:
        self.app_key = app_key
        self.base_url = f"https://www.betfair.{locale}/apuestas"

    def fetch_cards(
        self,
        urns: list[str],
        *,
        view_urn: str,
        current_url: str,
        referer: Optional[str] = None,
    ) -> dict[str, Any]:
        if not urns:
            return {"data": {"Cards": []}}

        params = urlencode(
            {
                "_ak": self.app_key,
                "currentViewUrn": view_urn,
                "currentUrl": current_url,
            }
        )
        url = f"{GQL_ENDPOINT}?{params}"
        body = {
            "variables": {
                "urn": urns,
                "numberOfFilledCardsInCardGroup": 2,
                "preferences": DEFAULT_PREFERENCES,
                "productExclusions": [],
                "experiments": DEFAULT_EXPERIMENTS,
            },
            "documentId": CARD_DOCUMENT_ID,
        }
        referer = referer or f"{self.base_url}/{current_url.lstrip('/')}"
        request = Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "*/*",
                "X-Application": self.app_key,
                "User-Agent": DEFAULT_USER_AGENT,
                "Referer": referer,
                "Origin": self.base_url.rsplit("/", 1)[0],
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise BetfairError(f"GraphQL HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise BetfairError(f"Error de red en GraphQL: {exc.reason}") from exc

        if payload.get("errors"):
            raise BetfairError(f"GraphQL error: {payload['errors']}")
        return payload


def extract_navigation_tab_urns(html: str, sport_path: str) -> list[str]:
    """Extrae URNs de pestañas de navegación embebidas en el HTML del deporte."""
    suffix = sport_urn_suffix(sport_path)
    pattern = rf"ppb:tbd:view:navigationTab:[A-Za-z0-9_]+{re.escape(suffix)}"
    return sorted(set(re.findall(pattern, html)))


def sport_urn_suffix(sport_path: str) -> str:
    """Convierte 'tenis/s-2' en '/s/2' para URNs de pestañas."""
    segment = sport_path.strip("/").split("/")[-1]
    if segment.startswith("s-"):
        return f"/{segment.replace('-', '/')}"
    return f"/{segment}"


def sport_view_urn(sport_path: str) -> str:
    segment = sport_path.strip("/").split("/")[-1]
    if segment.startswith("s-"):
        sport_id = segment.split("-", 1)[1]
        return f"ppb:tbd:view:sport:{sport_id}"
    return f"ppb:tbd:view:sport:{segment}"


def event_view_urn(event_id: int) -> str:
    return f"ppb:tbd:view:event:{event_id}"


def find_navigation_tab(cards: list[Any], title: str) -> Optional[dict[str, Any]]:
    target = title.lower().strip()
    for card in cards:
        if not isinstance(card, dict):
            continue
        if card.get("__typename") != "NavigationTab":
            continue
        tab_title = (card.get("tabTitle") or {}).get("translated", "")
        if tab_title.lower().strip() == target:
            return card
    return None
