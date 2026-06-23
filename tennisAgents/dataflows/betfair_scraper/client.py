"""Cliente HTTP para páginas de Betfair Sportsbook."""

from __future__ import annotations

import json
import re
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

DEFAULT_APP_KEY = "K61C39rIC0WKzoQ7"

SPORT_PATHS = {
    "tennis": "tenis/s-2",
    "tenis": "tenis/s-2",
    "football": "fútbol/s-1",
    "futbol": "fútbol/s-1",
    "basketball": "baloncesto/s-7522",
    "baloncesto": "baloncesto/s-7522",
}

CATALOG_VAR = "__TBD_PRELOADED_CATALOG__"


class BetfairError(Exception):
    """Error al consultar Betfair."""


class BetfairClient:
    """Descarga y parsea el catálogo precargado de Betfair."""

    def __init__(self, locale: str = "es") -> None:
        self.base_url = f"https://www.betfair.{locale}/apuestas"
        self.user_agent = DEFAULT_USER_AGENT
        self.app_key = DEFAULT_APP_KEY

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept-Language": "es-ES,es;q=0.9",
            "Accept": "text/html,application/xhtml+xml",
        }

    def fetch_page(self, path: str) -> str:
        path = path.lstrip("/")
        url = f"{self.base_url}/{path}"
        request = Request(url, headers=self._headers())
        try:
            with urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            raise BetfairError(f"HTTP {exc.code} al consultar {url}") from exc
        except URLError as exc:
            raise BetfairError(f"Error de red al consultar {url}: {exc.reason}") from exc

    @staticmethod
    def extract_app_key(html: str) -> str:
        marker = "window.__TBD_ENVIRONMENT__ = "
        start = html.find(marker)
        if start == -1:
            return DEFAULT_APP_KEY
        try:
            env, _ = json.JSONDecoder().raw_decode(html, start + len(marker))
            return env.get("APP_KEY") or DEFAULT_APP_KEY
        except json.JSONDecodeError:
            return DEFAULT_APP_KEY

    @staticmethod
    def extract_catalog(html: str) -> Optional[dict[str, Any]]:
        marker = f"window.{CATALOG_VAR} = "
        start = html.find(marker)
        if start == -1:
            return None
        try:
            catalog, _ = json.JSONDecoder().raw_decode(html, start + len(marker))
            return catalog
        except json.JSONDecodeError as exc:
            raise BetfairError(f"No se pudo parsear {CATALOG_VAR}: {exc}") from exc

    def fetch_page_bundle(self, path: str) -> tuple[str, dict[str, Any]]:
        html = self.fetch_page(path)
        self.app_key = self.extract_app_key(html)
        catalog = self.extract_catalog(html)
        if not catalog:
            raise BetfairError(f"La página no incluye catálogo precargado: {path}")
        return html, catalog

    def fetch_catalog(self, path: str) -> dict[str, Any]:
        _, catalog = self.fetch_page_bundle(path)
        return catalog

    def sport_path(self, sport: str) -> str:
        key = sport.lower().strip()
        if key not in SPORT_PATHS:
            options = ", ".join(sorted(set(SPORT_PATHS)))
            raise BetfairError(f"Deporte no soportado: {sport}. Opciones: {options}")
        return SPORT_PATHS[key]

    def discover_quicklink(self, sport: str, label: str) -> Optional[str]:
        """Busca una URL relativa en los accesos rápidos del deporte."""
        catalog = self.fetch_catalog(self.sport_path(sport))
        target = label.lower().strip()
        for group in catalog.get("data", {}).get("QuicklinksGridCardGroup", []):
            edges = group.get("items", {}).get("edges", [])
            for edge in edges:
                node = edge.get("node", {})
                edge_label = (
                    edge.get("label")
                    or node.get("genericViewLinkTitle", {}).get("name")
                    or ""
                ).lower()
                if target in edge_label:
                    view_url = node.get("viewLink", {}).get("viewUrl")
                    if view_url and not view_url.startswith("http"):
                        return view_url
        return None

    def discover_today_coupon(self, sport: str = "tennis") -> str:
        path = self.discover_quicklink(sport, "partidos de hoy")
        if not path:
            raise BetfairError("No se encontró el cupón 'Partidos de hoy' para el deporte.")
        return path

    def discover_inplay_path(self, sport: str = "tennis") -> str:
        path = self.discover_quicklink(sport, "en juego")
        if not path:
            return "en-directo/todos/i-696e706c6179"
        return path
