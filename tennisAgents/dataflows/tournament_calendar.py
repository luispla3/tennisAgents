"""Consulta de calendarios oficiales ATP Tour y Challenger 2026."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_CHALLENGER_CALENDAR_PATH = _DATA_DIR / "atp_challenger_calendar_2026.json"
_ATP_TOUR_CALENDAR_PATH = _DATA_DIR / "atp_tour_calendar_2026.json"

_OFFICIAL_CATEGORY_TO_CODE = {
    "grand_slam": "gs",
    "masters_1000": "1000",
    "atp_500": "atp",
    "atp_250": "atp",
    "atp_finals": "atp",
    "next_gen": "atp",
    "davis_cup": "atp",
    "laver_cup": "atp",
    "united_cup": "atp",
    "challenger": "ch",
}


@dataclass(frozen=True)
class OfficialTournament:
    name: str
    location: str | None
    surface: str | None
    category: str
    category_label: str
    calendar: str
    tier: int | None = None
    search_keys: tuple[str, ...] = ()


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_calendar_key(text: str) -> str:
    text = _strip_accents(str(text or "")).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\bchallenger\b", " ", text)
    text = re.sub(r"\b(atp|men|singles|individual|masculino)\b", " ", text)
    return " ".join(text.split())


def _normalize_surface(raw: str | None) -> str | None:
    if not raw:
        return None
    key = _strip_accents(raw).lower().strip()
    mapping = {
        "hard": "hard",
        "clay": "clay",
        "grass": "grass",
        "carpet": "carpet",
    }
    return mapping.get(key)


def _location_parts(location: str | None) -> tuple[str, str]:
    if not location:
        return "", ""
    if "," in location:
        city, country = [part.strip() for part in location.split(",", 1)]
        return normalize_calendar_key(city), normalize_calendar_key(country)
    return normalize_calendar_key(location), ""


def locations_match(provided: str | None, official: str | None) -> bool:
    """True si la ubicación proporcionada es compatible con la del calendario oficial."""
    if not provided or not official:
        return False

    provided_key = normalize_calendar_key(provided)
    official_key = normalize_calendar_key(official)
    if not provided_key or not official_key:
        return False
    if provided_key == official_key:
        return True
    if official_key in provided_key or provided_key in official_key:
        return True

    provided_city, provided_country = _location_parts(provided)
    official_city, official_country = _location_parts(official)
    if provided_city and official_city and provided_city == official_city:
        if not provided_country or not official_country or provided_country == official_country:
            return True
    return False


def official_category_code(category: str) -> str:
    return _OFFICIAL_CATEGORY_TO_CODE.get(category, "unknown")


@lru_cache(maxsize=1)
def _load_official_tournaments() -> tuple[OfficialTournament, ...]:
    tournaments: list[OfficialTournament] = []

    def append_from_payload(payload: dict, calendar: str) -> None:
        for item in payload.get("tournaments") or []:
            category = str(item.get("category") or ("challenger" if calendar == "challenger" else "atp_250"))
            keys = {normalize_calendar_key(item.get("name") or "")}
            for key in item.get("search_keys") or []:
                keys.add(normalize_calendar_key(key))
            location = item.get("location") or ""
            if location and "," in location:
                keys.add(normalize_calendar_key(location.split(",", 1)[0].strip()))
            elif location:
                keys.add(normalize_calendar_key(location))
            keys.discard("")
            tournaments.append(
                OfficialTournament(
                    name=str(item.get("name") or ""),
                    location=item.get("location") or None,
                    surface=_normalize_surface(item.get("surface")),
                    category=category,
                    category_label=str(item.get("category_label") or category),
                    calendar=calendar,
                    tier=item.get("tier"),
                    search_keys=tuple(sorted(keys)),
                )
            )

    if _CHALLENGER_CALENDAR_PATH.exists():
        append_from_payload(json.loads(_CHALLENGER_CALENDAR_PATH.read_text(encoding="utf-8")), "challenger")
    if _ATP_TOUR_CALENDAR_PATH.exists():
        append_from_payload(json.loads(_ATP_TOUR_CALENDAR_PATH.read_text(encoding="utf-8")), "atp_tour")
    return tuple(tournaments)


@lru_cache(maxsize=1)
def _lookup_index() -> tuple[tuple[str, int], ...]:
    index: list[tuple[str, int]] = []
    tournaments = _load_official_tournaments()
    for idx, tournament in enumerate(tournaments):
        for key in tournament.search_keys:
            if key:
                index.append((key, idx))
    index.sort(key=lambda pair: len(pair[0]), reverse=True)
    return tuple(index)


def find_official_tournament(text: str) -> OfficialTournament | None:
    """Devuelve el torneo oficial que mejor encaja con el texto recibido."""
    normalized = normalize_calendar_key(text)
    if not normalized:
        return None

    tournaments = _load_official_tournaments()
    for key, idx in _lookup_index():
        if normalized == key or (len(key) >= 5 and key in normalized):
            return tournaments[idx]
    return None


def _matches_official_calendar(text: str, calendar: str) -> bool:
    tournament = find_official_tournament(text)
    return tournament is not None and tournament.calendar == calendar


def matches_official_challenger_calendar(text: str) -> bool:
    return _matches_official_calendar(text, "challenger")


def matches_official_atp_tour_calendar(text: str) -> bool:
    return _matches_official_calendar(text, "atp_tour")


def resolve_official_location(tournament: str, provided_location: str | None = None) -> tuple[str | None, bool, OfficialTournament | None]:
    """
    Resuelve la ubicación para meteorología.

    Returns:
        (ubicación_recomendada, verificada_con_calendario, torneo_oficial)
    """
    official = find_official_tournament(tournament or provided_location or "")
    if not official or not official.location:
        return provided_location, False, official

    if provided_location and locations_match(provided_location, official.location):
        return official.location, True, official

    if provided_location and not locations_match(provided_location, official.location):
        return official.location, False, official

    return official.location, True, official
