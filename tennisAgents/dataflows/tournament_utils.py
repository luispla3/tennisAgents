from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from tennisAgents.dataflows.config import get_config
from tennisAgents.dataflows.llm_utils import invoke_chat_llm, invoke_local_analyst_llm
from tennisAgents.dataflows.web_search_utils import perform_web_search


@dataclass(frozen=True)
class TournamentIdentity:
    """Representación normalizada de un torneo independiente del formato de origen."""

    raw: str
    display_name: str
    search_name: str
    location: str | None
    surface: str | None
    category: str


SURFACE_ALIASES: dict[str, str] = {
    "clay": "clay",
    "arcilla": "clay",
    "tierra": "clay",
    "tierra batida": "clay",
    "terre battue": "clay",
    "hard": "hard",
    "duro": "hard",
    "cemento": "hard",
    "grass": "grass",
    "hierba": "grass",
    "cesped": "grass",
    "césped": "grass",
}

COUNTRY_ALIASES: dict[str, str] = {
    "italy": "Italy",
    "italia": "Italy",
    "switzerland": "Switzerland",
    "schweiz": "Switzerland",
    "suisse": "Switzerland",
    "sweden": "Sweden",
    "sverige": "Sweden",
    "spain": "Spain",
    "espana": "Spain",
    "españa": "Spain",
    "france": "France",
    "germany": "Germany",
    "deutschland": "Germany",
    "united kingdom": "United Kingdom",
    "uk": "United Kingdom",
    "great britain": "United Kingdom",
    "england": "United Kingdom",
    "usa": "United States",
    "united states": "United States",
    "u.s.a.": "United States",
    "australia": "Australia",
    "monaco": "Monaco",
    "austria": "Austria",
    "croatia": "Croatia",
    "serbia": "Serbia",
    "romania": "Romania",
    "canada": "Canada",
    "china": "China",
    "japan": "Japan",
    "mexico": "Mexico",
    "brazil": "Brazil",
    "argentina": "Argentina",
    "chile": "Chile",
    "colombia": "Colombia",
    "portugal": "Portugal",
    "netherlands": "Netherlands",
    "belgium": "Belgium",
    "poland": "Poland",
    "czech republic": "Czech Republic",
    "czechia": "Czech Republic",
    "hungary": "Hungary",
    "turkey": "Turkey",
    "greece": "Greece",
    "norway": "Norway",
    "denmark": "Denmark",
    "finland": "Finland",
    "ireland": "Ireland",
    "south africa": "South Africa",
    "india": "India",
    "qatar": "Qatar",
    "uae": "United Arab Emirates",
    "united arab emirates": "United Arab Emirates",
}

CATEGORY_LABELS: dict[str, str] = {
    "gs": "Grand Slam",
    "1000": "Masters 1000",
    "atp": "ATP",
    "ch": "Challenger",
    "wta": "WTA",
    "itf": "ITF",
    "unknown": "Torneo",
}

_CITY_COUNTRY_RE = re.compile(
    r"^(?P<city>.+?)\s*\(\s*(?P<country>[^)]+?)\s*\)\s*$",
    re.IGNORECASE,
)
_TRAILING_SURFACE_RE = re.compile(
    r"(?:,\s*|\s+)(?P<surface>clay|hard|grass|arcilla|hierba|cesped|césped|duro|tierra(?:\s+batida)?)\s*$",
    re.IGNORECASE,
)
_CATEGORY_NOISE_RE = re.compile(
    r"\b("
    r"challenger|challengers|atp|wta|itf|men|women|womens|"
    r"singles|doubles|qualifying|qualification|"
    r"masculino|femenino|individual|"
    r"grand\s+slam|masters\s*1000|masters|"
    r"\b250\b|\b500\b|\b1000\b"
    r")\b",
    re.IGNORECASE,
)
_SUFFIX_NOISE_RE = re.compile(r"\s+(?:ch|atp|wta|itf|m\d+)\s*$", re.IGNORECASE)


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _clean_spaces(text: str) -> str:
    return " ".join(text.replace("_", " ").split()).strip(" ,-")


def _normalize_country(raw_country: str) -> str:
    key = _strip_accents(raw_country).lower().strip()
    return COUNTRY_ALIASES.get(key, raw_country.strip().title())


def _normalize_surface(raw_surface: str | None) -> str | None:
    if not raw_surface:
        return None
    key = _strip_accents(raw_surface).lower().strip()
    return SURFACE_ALIASES.get(key)


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


def _extract_surface(text: str) -> tuple[str, str | None]:
    match = _TRAILING_SURFACE_RE.search(text)
    if not match:
        return text, None
    surface = _normalize_surface(match.group("surface"))
    cleaned = _clean_spaces(text[: match.start()])
    return cleaned, surface


def _extract_city_country(text: str) -> tuple[str | None, str | None, str]:
    cleaned, surface = _extract_surface(text)
    match = _CITY_COUNTRY_RE.match(cleaned)
    if match:
        city = _clean_spaces(match.group("city"))
        country = _normalize_country(match.group("country"))
        remainder = _clean_spaces(cleaned[match.end() :])
        if remainder:
            city = _clean_spaces(f"{city} {remainder}")
        return city, country, surface or _normalize_surface(remainder)

    if "," in cleaned:
        left, right = [part.strip() for part in cleaned.rsplit(",", 1)]
        if left and right and len(right.split()) <= 3 and not _normalize_surface(right):
            return _clean_spaces(left), _normalize_country(right), surface

    return _clean_spaces(cleaned), None, surface


def _title_case_preserve_acronyms(text: str) -> str:
    words = []
    for word in text.split():
        if word.isupper() and len(word) <= 4:
            words.append(word)
        else:
            words.append(word[:1].upper() + word[1:].lower() if word else word)
    return " ".join(words)


def _clean_search_name(city: str) -> str:
    cleaned = _CATEGORY_NOISE_RE.sub(" ", city)
    cleaned = _SUFFIX_NOISE_RE.sub("", cleaned)
    cleaned = _clean_spaces(cleaned)
    return _title_case_preserve_acronyms(cleaned)


def _build_display_name(search_name: str, country: str | None, category: str, surface: str | None) -> str:
    parts = [search_name]
    if country:
        parts[0] = f"{search_name} ({country})"
    label = CATEGORY_LABELS.get(category, "Torneo")
    if category != "unknown":
        parts.append(label)
    if surface:
        parts.append(surface)
    return " · ".join(parts)


LOCATION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Gstaad, Switzerland": ("gstaad", "swiss open"),
    "Bastad, Sweden": ("bastad", "båstad", "swedish open", "nordea open"),
    "Cordenons, Italy": ("cordenons", "challenger cordenons"),
    "Monte Carlo, Monaco": ("monte carlo", "montecarlo"),
    "Madrid, Spain": ("madrid", "mutua"),
    "Rome, Italy": ("rome", "roma", "internazionali"),
    "Paris, France": ("roland garros", "french open", "paris"),
    "London, United Kingdom": ("wimbledon", "queens", "queen's"),
    "New York, United States": ("us open", "flushing"),
    "Melbourne, Australia": ("australian open", "melbourne"),
}

SURFACE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "clay": (
        "clay", "arcilla", "tierra", "roland garros", "french open",
        "monte carlo", "madrid", "rome", "barcelona", "gstaad", "bastad",
        "umag", "hamburg", "kitzbuhel", "cordenons",
    ),
    "grass": ("grass", "hierba", "cesped", "césped", "wimbledon", "queens", "halle", "stuttgart"),
    "hard": ("hard", "duro", "us open", "australian open", "miami", "indian wells", "cincinnati"),
}


KNOWN_TOURNAMENTS = {
    "gstaad": {
        "name": "Swiss Open Gstaad",
        "location": "Gstaad, Switzerland",
        "surface": "clay",
        "category": "ATP 250",
        "altitude": "aprox. 1.050 m",
        "notes": (
            "Torneo ATP sobre tierra batida en altitud moderada. La altitud hace que "
            "la pelota pueda viajar algo más rápido que en otros torneos de arcilla, "
            "manteniendo rallies propios de clay pero premiando también potencia y saque."
        ),
    },
    "bastad": {
        "name": "Nordea Open / Swedish Open Bastad",
        "location": "Bastad, Sweden",
        "surface": "clay",
        "category": "ATP 250",
        "altitude": "nivel del mar",
        "notes": (
            "Torneo tradicional de tierra batida. Condiciones generalmente más lentas "
            "que Gstaad por menor altitud; suele favorecer consistencia desde fondo, "
            "movilidad y resistencia en intercambios largos."
        ),
    },
    "cordenons": {
        "name": "ATP Challenger Cordenons",
        "location": "Cordenons, Italy",
        "surface": "clay",
        "category": "Challenger",
        "altitude": "nivel del mar",
        "notes": (
            "Challenger ATP sobre tierra batida en Friuli-Venezia Giulia (Italia). "
            "Arcilla lenta típica del circuito italiano; favorece consistencia desde fondo, "
            "movilidad y resistencia en rallies largos."
        ),
    },
}


def _lookup_location_from_text(text: str) -> str | None:
    lower = _strip_accents(text).lower()
    for key, info in KNOWN_TOURNAMENTS.items():
        if key in lower:
            return info["location"]
    for location, keywords in LOCATION_KEYWORDS.items():
        if any(keyword in lower for keyword in keywords):
            return location
    return None


def _lookup_surface_from_text(text: str) -> str | None:
    lower = _strip_accents(text).lower()
    for key, info in KNOWN_TOURNAMENTS.items():
        if key in lower:
            return info["surface"]
    for surface, keywords in SURFACE_KEYWORDS.items():
        if any(keyword in lower for keyword in keywords):
            return surface
    return None


def normalize_tournament(raw: str) -> TournamentIdentity:
    """
    Normaliza nombres de torneo desde Betfair, Flashscore, ATP o texto libre.

    Ejemplos:
    - CHALLENGER MEN - SINGLES: Cordenons (Italy), clay
    - Swiss Open Gstaad
    - Cordenons CH
    - Wimbledon
    """
    original = _clean_spaces(raw or "")
    if not original:
        return TournamentIdentity(
            raw=raw or "",
            display_name="Torneo desconocido",
            search_name="",
            location=None,
            surface=None,
            category="unknown",
        )

    category = _detect_category(original)
    working = original

    if ":" in working:
        working = working.split(":")[-1].strip()

    working = re.sub(r"^[\-\s]+", "", working)
    city, country, surface = _extract_city_country(working)

    if not surface:
        surface = _normalize_surface(working) or _lookup_surface_from_text(original)

    if city:
        search_name = _clean_search_name(city)
        location = f"{search_name}, {country}" if country else None
    else:
        search_name = _clean_search_name(working)
        location = None

    if not location:
        location = _lookup_location_from_text(search_name) or _lookup_location_from_text(original)

    if not search_name:
        search_name = _clean_search_name(original)

    if not surface:
        surface = _lookup_surface_from_text(search_name) or _lookup_surface_from_text(original)

    display_name = _build_display_name(search_name, country, category, surface)

    return TournamentIdentity(
        raw=original,
        display_name=display_name,
        search_name=search_name,
        location=location,
        surface=surface,
        category=category,
    )


def _known_tournament_report(tournament_name: str, date: str) -> str:
    identity = normalize_tournament(tournament_name)
    lookup_keys = (
        identity.search_name.lower(),
        identity.raw.lower(),
        tournament_name.lower(),
    )
    for key, info in KNOWN_TOURNAMENTS.items():
        if any(key in candidate for candidate in lookup_keys if candidate):
            return (
                f"## Información verificada del torneo\n\n"
                f"- Torneo: {info['name']}\n"
                f"- Nombre normalizado: {identity.display_name}\n"
                f"- Fecha analizada: {date}\n"
                f"- Ubicación: {info['location']}\n"
                f"- Superficie: {info['surface']}\n"
                f"- Categoría: {info['category']}\n"
                f"- Altitud: {info['altitude']}\n"
                f"- Fuente: conocimiento estructurado local del sistema + nombre recibido: "
                f"`{tournament_name}`\n\n"
                f"## Impacto tenístico\n\n{info['notes']}"
            )
    return ""


def resolve_tournament_location(tournament_name: str) -> str | None:
    """Resuelve ciudad/país para geocoding meteorológico desde el nombre del torneo."""
    identity = normalize_tournament(tournament_name)
    if identity.location:
        return identity.location
    return _lookup_location_from_text(identity.search_name) or _lookup_location_from_text(tournament_name or "")


def resolve_tournament_surface(tournament_name: str) -> str | None:
    """Resuelve clay/hard/grass desde el nombre del torneo."""
    identity = normalize_tournament(tournament_name)
    if identity.surface:
        return identity.surface
    return _lookup_surface_from_text(identity.search_name) or _lookup_surface_from_text(tournament_name or "")


def get_tournament_info_openai(tournament_name: str, category: str, date: str) -> str:
    config = get_config()
    identity = normalize_tournament(tournament_name)
    effective_category = category if category and category != "atp" else identity.category
    if effective_category == "unknown":
        effective_category = "atp"

    known_report = _known_tournament_report(identity.search_name or tournament_name, date)
    if known_report:
        return known_report

    search_name = identity.search_name or tournament_name
    search_location = identity.location or search_name

    if config.get("use_local_analysts", False):
        try:
            text, label = invoke_local_analyst_llm(
                "Eres un experto en torneos de tenis ATP y Grand Slam.",
                (
                    f"Genera un informe simulado sobre el torneo {identity.display_name} "
                    f"(Categoría: {effective_category}). Describe las características típicas de este torneo: "
                    f"superficie, velocidad de pista, condiciones habituales y contexto histórico. "
                    f"Menciona que este análisis es basado en conocimiento general del modelo y no "
                    f"en datos en tiempo real."
                ),
            )
            return f"[ANÁLISIS VIA {label} - SIN BÚSQUEDA WEB EN TIEMPO REAL]\n{text}"
        except Exception as e:
            return f"Error usando modelo para torneo: {str(e)}"

    search_context = perform_web_search(
        f"{search_name} {search_location} tennis tournament {effective_category} {date} draw schedule surface"
    )
    return invoke_chat_llm(
        (
            f"Resume información actual sobre el torneo {identity.display_name} "
            f"el día {date} en la categoría {effective_category}."
        ),
        f"Resultados de búsqueda web:\n\n{search_context}",
    )

