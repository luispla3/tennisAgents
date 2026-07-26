"""Detección de categoría de torneo: ATP Challenger o superior."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

_CALENDAR_MODULE = "tennisAgents.dataflows.tournament_calendar"


def _calendar_module():
    if _CALENDAR_MODULE in sys.modules:
        return sys.modules[_CALENDAR_MODULE]
    path = Path(__file__).with_name("tournament_calendar.py")
    spec = importlib.util.spec_from_file_location(_CALENDAR_MODULE, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[_CALENDAR_MODULE] = module
    spec.loader.exec_module(module)
    return module


_cal = _calendar_module()
matches_official_challenger_calendar = _cal.matches_official_challenger_calendar
matches_official_atp_tour_calendar = _cal.matches_official_atp_tour_calendar

_ITF_KEYWORDS = (
    "itf",
    "futures",
    "world tennis tour",
    "m15",
    "m25",
    "w15",
    "w25",
    "utr",
    "exhibition",
)
_ATP_TOUR_KEYWORDS = (
    "grand slam",
    "wimbledon",
    "roland garros",
    "french open",
    "us open",
    "australian open",
    "masters 1000",
    "masters",
    "m1000",
    "atp 250",
    "atp 500",
    "atp 1000",
    "atp finals",
    "next gen",
    "davis cup",
    "laver cup",
    "united cup",
    "olympic",
    "olympics",
    "atp cup",
)
_CHALLENGER_KEYWORDS = ("challenger",)


def _strip_accents(text: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _detect_category(text: str) -> str:
    lower = _strip_accents(text).lower()
    if "challenger" in lower or re.search(r"\bch\b", lower):
        return "ch"
    if any(
        token in lower
        for token in (
            "grand slam",
            "wimbledon",
            "roland garros",
            "french open",
            "us open",
            "australian open",
        )
    ):
        return "gs"
    if "1000" in lower or "masters" in lower or "m1000" in lower:
        return "1000"
    if "wta" in lower:
        return "wta"
    if "itf" in lower or re.search(r"\bm\d+\b", lower):
        return "itf"
    if "atp" in lower or "250" in lower or "500" in lower:
        return "atp"
    return "unknown"


def _match_blob(match: dict[str, Any]) -> str:
    return " ".join(
        str(match.get(key) or "")
        for key in ("competition", "tournament", "category", "name")
    ).lower()


def is_itf_or_lower_tournament(text: str) -> bool:
    lower = _strip_accents(text).lower()
    if any(token in lower for token in _ITF_KEYWORDS):
        return True
    if re.search(r"\bm\d+\b", lower):
        return True
    if "wta" in lower or "women" in lower or "femenin" in lower:
        return True
    category = _detect_category(text)
    return category == "itf"


def is_atp_challenger_or_higher_match(match: dict[str, Any]) -> bool:
    """
    True si el partido pertenece a ATP Challenger o categoría superior.

    Incluye Grand Slam, ATP Tour (250/500/1000), Masters y Challenger.
    Excluye ITF, Futures, WTA y categorías inferiores.
    """
    blob = _match_blob(match)
    if not blob.strip():
        return False

    if is_itf_or_lower_tournament(blob):
        return False

    if any(token in blob for token in _CHALLENGER_KEYWORDS):
        return True

    category = _detect_category(blob)
    if category in {"gs", "1000", "atp", "ch"}:
        return True

    if any(token in blob for token in _ATP_TOUR_KEYWORDS):
        return True

    if re.search(r"\batp\b", blob) and "itf" not in blob:
        return True

    if matches_official_challenger_calendar(blob):
        return True

    if matches_official_atp_tour_calendar(blob):
        return True

    return False


def filter_atp_challenger_or_higher_matches(
    matches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [m for m in matches if is_atp_challenger_or_higher_match(m)]
