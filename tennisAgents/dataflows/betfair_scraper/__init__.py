"""Scraper de Betfair Sportsbook: partidos en vivo y cuotas."""

from .client import BetfairClient, BetfairError, SPORT_PATHS
from .parser import parse_catalog
from .scraper import (
    get_event_markets,
    get_live_matches,
    get_matches,
)

__all__ = [
    "BetfairClient",
    "BetfairError",
    "SPORT_PATHS",
    "parse_catalog",
    "get_matches",
    "get_live_matches",
    "get_event_markets",
]

__version__ = "1.0.0"
