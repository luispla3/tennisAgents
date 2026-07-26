from __future__ import annotations

import importlib.util
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from tennisAgents.dataflows.config import get_config
from tennisAgents.dataflows.llm_utils import invoke_chat_llm, invoke_local_analyst_llm
from tennisAgents.dataflows.web_search_utils import perform_web_search
from tennisAgents.utils.enumerations import STATE

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
find_official_tournament = _cal.find_official_tournament
locations_match = _cal.locations_match
official_category_code = _cal.official_category_code


@dataclass(frozen=True)
class TournamentIdentity:
    """Representación normalizada de un torneo independiente del formato de origen."""

    raw: str
    display_name: str
    search_name: str
    location: str | None
    surface: str | None
    category: str
    official_name: str | None = None
    calendar_source: str | None = None
    location_from_calendar: bool = False
    location_verified: bool = False


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
    "san marino": {
        "name": "San Marino ATP Challenger",
        "location": "San Marino, San Marino",
        "surface": "clay",
        "category": "Challenger",
        "altitude": "nivel del mar",
        "notes": (
            "Challenger ATP sobre tierra batida en San Marino. Arcilla outdoor típica "
            "del circuito italiano; favorece consistencia desde fondo y rallies largos."
        ),
    },
    "liberec": {
        "name": "Liberec Challenger",
        "location": "Liberec, Czech Republic",
        "surface": "clay",
        "category": "Challenger",
        "altitude": "nivel del mar",
        "notes": (
            "Challenger ATP sobre tierra batida en República Checa. Superficie lenta "
            "que premia solidez desde el fondo y resistencia física."
        ),
    },
    "samsun": {
        "name": "Samsun Challenger",
        "location": "Samsun, Turkey",
        "surface": "hard",
        "category": "Challenger",
        "altitude": "nivel del mar",
        "notes": (
            "Challenger ATP sobre pista dura outdoor en la costa del Mar Negro. "
            "Superficie intermedia que favorece equilibrio entre saque y fondo."
        ),
    },
}


def _keyword_in_text(keyword: str, text: str) -> bool:
    """Coincidencia segura: palabras completas para tokens simples; frase para multi-palabra."""
    keyword = _strip_accents(keyword).lower().strip()
    haystack = _strip_accents(text).lower()
    if not keyword or not haystack:
        return False
    if " " in keyword:
        return keyword in haystack
    return re.search(rf"\b{re.escape(keyword)}\b", haystack) is not None


def _has_explicit_surface(text: str) -> bool:
    if not text:
        return False
    _, surface = _extract_surface(text)
    return bool(surface or _TRAILING_SURFACE_RE.search(text))


def resolve_tournament_raw(
    *,
    betfair_competition: str | None = None,
    flashscore_tournament: str | None = None,
    stored: str | None = None,
) -> str:
    """
    Elige el mejor texto de torneo según prioridad de fuentes.

    Orden: Flashscore (superficie/ubicación explícitas) > almacenado > Betfair.
    """
    candidates: list[tuple[str, str | None]] = [
        ("flashscore", flashscore_tournament),
        ("stored", stored),
        ("betfair", betfair_competition),
    ]

    for _source, value in candidates:
        if value and _has_explicit_surface(value):
            return _clean_spaces(str(value))

    if flashscore_tournament:
        return _clean_spaces(str(flashscore_tournament))
    if stored:
        return _clean_spaces(str(stored))
    if betfair_competition:
        return _clean_spaces(str(betfair_competition))
    return "Tennis"


def _country_from_location(location: str | None) -> str | None:
    if location and "," in location:
        return _normalize_country(location.split(",", 1)[1].strip())
    return None


def _rebuild_identity_surface(
    identity: TournamentIdentity,
    surface: str,
    *,
    raw: str | None = None,
) -> TournamentIdentity:
    return TournamentIdentity(
        raw=raw or identity.raw,
        display_name=_build_display_name(
            identity.search_name,
            _country_from_location(identity.location),
            identity.category,
            surface,
        ),
        search_name=identity.search_name,
        location=identity.location,
        surface=surface,
        category=identity.category,
        official_name=identity.official_name,
        calendar_source=identity.calendar_source,
        location_from_calendar=identity.location_from_calendar,
        location_verified=identity.location_verified,
    )


def _flashscore_location_hint(flashscore_tournament: str | None) -> str | None:
    if not flashscore_tournament:
        return None
    working = (
        flashscore_tournament.split(":")[-1].strip()
        if ":" in flashscore_tournament
        else flashscore_tournament
    )
    city, country, _ = _extract_city_country(working)
    if not city:
        return None
    search = _clean_search_name(city)
    return f"{search}, {country}" if country else search


def resolve_tournament_identity(
    *,
    betfair_competition: str | None = None,
    flashscore_tournament: str | None = None,
    stored: str | None = None,
) -> TournamentIdentity:
    """
    Resuelve identidad normalizada del torneo fusionando Betfair, Flashscore y meta.

    Flashscore con superficie explícita prevalece sobre heurísticas cuando no hay
    entrada en el calendario oficial.
    """
    raw = resolve_tournament_raw(
        betfair_competition=betfair_competition,
        flashscore_tournament=flashscore_tournament,
        stored=stored,
    )
    identity = normalize_tournament(raw)

    flash_surface = _heuristic_surface_hint(flashscore_tournament or "")
    flash_explicit = _has_explicit_surface(flashscore_tournament or "")

    if flash_surface and flash_explicit and not identity.official_name:
        if identity.surface != flash_surface:
            identity = _rebuild_identity_surface(identity, flash_surface, raw=raw)

    if not identity.location:
        flash_loc = _flashscore_location_hint(flashscore_tournament)
        if flash_loc:
            search = flash_loc.split(",", 1)[0].strip()
            identity = TournamentIdentity(
                raw=raw,
                display_name=_build_display_name(
                    _clean_search_name(search),
                    _country_from_location(flash_loc),
                    identity.category,
                    identity.surface,
                ),
                search_name=_clean_search_name(search),
                location=flash_loc,
                surface=identity.surface,
                category=identity.category,
                official_name=identity.official_name,
                calendar_source=identity.calendar_source,
                location_from_calendar=identity.location_from_calendar,
                location_verified=identity.location_verified,
            )

    return identity


def _lookup_location_from_text(text: str) -> str | None:
    for key, info in KNOWN_TOURNAMENTS.items():
        if _keyword_in_text(key, text):
            return info["location"]
    for location, keywords in LOCATION_KEYWORDS.items():
        if any(_keyword_in_text(keyword, text) for keyword in keywords):
            return location
    return None


def _lookup_surface_from_text(text: str) -> str | None:
    for key, info in KNOWN_TOURNAMENTS.items():
        if _keyword_in_text(key, text):
            return info["surface"]
    for surface, keywords in SURFACE_KEYWORDS.items():
        if any(_keyword_in_text(keyword, text) for keyword in keywords):
            return surface
    return None


def _apply_official_calendar(
    identity: TournamentIdentity,
    *,
    parsed_location: str | None,
) -> TournamentIdentity:
    official = find_official_tournament(identity.raw) or find_official_tournament(identity.search_name)
    if not official:
        return identity

    category = official_category_code(official.category)
    if category == "unknown":
        category = identity.category

    search_name = official.name or identity.search_name
    location = official.location or identity.location
    # Calendario oficial prevalece sobre heurísticas (p. ej. grass por falso positivo).
    surface = official.surface if official.surface else identity.surface

    country = None
    if location and "," in location:
        country = _normalize_country(location.split(",", 1)[1].strip())

    display_name = _build_display_name(search_name, country, category, surface)
    location_verified = bool(
        parsed_location and official.location and locations_match(parsed_location, official.location)
    )

    return TournamentIdentity(
        raw=identity.raw,
        display_name=display_name,
        search_name=search_name,
        location=location,
        surface=surface,
        category=category,
        official_name=official.name,
        calendar_source=official.calendar,
        location_from_calendar=bool(official.location),
        location_verified=location_verified,
    )


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

    explicit_surface = surface or _normalize_surface(working)
    if not explicit_surface:
        explicit_surface = _lookup_surface_from_text(original)

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

    surface = explicit_surface
    if not surface:
        surface = _lookup_surface_from_text(search_name) or _lookup_surface_from_text(original)

    display_name = _build_display_name(search_name, country, category, surface)

    identity = TournamentIdentity(
        raw=original,
        display_name=display_name,
        search_name=search_name,
        location=location,
        surface=surface,
        category=category,
    )
    return _apply_official_calendar(identity, parsed_location=location)


SURFACE_IMPACT_NOTES: dict[str, str] = {
    "clay": (
        "Arcilla outdoor: superficie lenta con bote alto y más grip. Favorece "
        "intercambios largos, movilidad lateral, consistencia desde el fondo y "
        "resistencia física. El saque pesa menos que en pistas rápidas; el "
        "segundo servicio y la paciencia en puntos largos suelen ser decisivos."
    ),
    "grass": (
        "Hierba: bote bajo y rápido, partidos más cortos y mayor peso del saque "
        "y la volea. La adaptación a deslizamientos, slice y transiciones rápidas "
        "a la red marca diferencias frente a especialistas de fondo."
    ),
    "hard": (
        "Pista dura: superficie intermedia en velocidad y altura de bote. Premia "
        "equilibrio entre saque, resto y solidez desde el fondo; condiciones "
        "habitualmente más predecibles que arcilla o hierba."
    ),
}

CHALLENGER_FORMAT_NOTE = (
    "Formato ATP Challenger: cuadro de 32-48 jugadores, partidos al mejor de "
    "3 sets con tie-break en todos los sets, puntos ATP para progresión de "
    "ranking y acceso al cuadro principal de torneos mayores."
)


def _heuristic_surface_hint(text: str) -> str | None:
    """Superficie inferida solo por texto/heurística, sin calendario oficial."""
    if not text:
        return None
    working = text.split(":")[-1].strip() if ":" in text else text
    _, surface = _extract_surface(working)
    if surface:
        return surface
    return _lookup_surface_from_text(text)


def build_analyst_tournament_context(
    resolved_raw: str,
    *,
    betfair_competition: str | None = None,
    flashscore_tournament: str | None = None,
    stored: str | None = None,
) -> str:
    """
    Banner compartido para todos los analistas con datos verificados del torneo.
    """
    identity = resolve_tournament_identity(
        betfair_competition=betfair_competition or resolved_raw,
        flashscore_tournament=flashscore_tournament,
        stored=stored or resolved_raw,
    )
    lines = [
        "CONTEXTO VERIFICADO DEL TORNEO (fuente de verdad para superficie, ubicación y categoría):",
        f"- Nombre normalizado: {identity.display_name}",
        f"- Superficie verificada: {identity.surface or 'N/D'}",
        f"- Ubicación: {identity.location or 'N/D'}",
        f"- Categoría: {CATEGORY_LABELS.get(identity.category, identity.category)}",
    ]

    if identity.official_name:
        source = "calendario ATP Challenger 2026" if identity.calendar_source == "challenger" else "calendario ATP Tour 2026"
        lines.append(f"- Torneo oficial: {identity.official_name} ({source})")

    flash_surface = _heuristic_surface_hint(flashscore_tournament or "")
    if flashscore_tournament and flash_surface:
        if identity.surface and flash_surface == identity.surface:
            lines.append(f"- Superficie confirmada por Flashscore: {flash_surface}.")
        elif identity.surface and flash_surface != identity.surface:
            lines.append(
                f"- ATENCIÓN: Flashscore indicaba «{flash_surface}»; "
                f"se usa «{identity.surface}» (calendario oficial)."
            )

    betfair_surface = _heuristic_surface_hint(betfair_competition or "")
    if (
        betfair_competition
        and betfair_surface
        and identity.surface
        and betfair_surface != identity.surface
    ):
        lines.append(
            f"- ATENCIÓN: la competición Betfair sugería «{betfair_surface}»; "
            f"se usa «{identity.surface}» (Flashscore/calendario oficial)."
        )

    lines.append(
        "Obligatorio: analiza clima, jugadores, noticias e impacto del torneo "
        "usando la superficie verificada anterior, no suposiciones del nombre Betfair."
    )
    return "\n".join(lines)


def merge_analyst_tournament_context(state: dict, additional_context: str) -> str:
    """Antepone el banner de torneo verificado al contexto de un analista."""
    banner = str(
        state.get(STATE.tournament_context) or state.get("tournament_context") or ""
    ).strip()
    if not banner:
        return additional_context
    return f"{banner}\n\n{additional_context}"


def _known_tournament_report(tournament_name: str, date: str) -> str:
    identity = resolve_tournament_identity(stored=tournament_name)
    if identity.official_name and identity.location:
        source = "calendario oficial ATP 2026"
        if identity.calendar_source == "challenger":
            source = "calendario oficial ATP Challenger 2026"
        report = (
            f"## Información verificada del torneo\n\n"
            f"- Torneo: {identity.official_name}\n"
            f"- Nombre normalizado: {identity.display_name}\n"
            f"- Fecha analizada: {date}\n"
            f"- Ubicación: {identity.location}\n"
            f"- Superficie: {identity.surface or 'N/D'}\n"
            f"- Categoría: {CATEGORY_LABELS.get(identity.category, identity.category)}\n"
            f"- Fuente: {source} + nombre recibido: `{tournament_name}`\n"
        )
        if identity.category == "ch":
            report += f"\n## Formato del torneo\n\n{CHALLENGER_FORMAT_NOTE}\n"
        if identity.surface and identity.surface in SURFACE_IMPACT_NOTES:
            report += (
                f"\n## Impacto tenístico de la superficie\n\n"
                f"{SURFACE_IMPACT_NOTES[identity.surface]}\n"
            )
        report += (
            "\n## Implicaciones analíticas\n\n"
            "Este informe proviene del calendario oficial integrado en el sistema. "
            "No requiere búsqueda web adicional. Usa estos datos como base para "
            "evaluar ventajas de estilo, fatiga, adaptación a la superficie y "
            "condiciones habituales del entorno del torneo."
        )
        return report

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


def resolve_weather_location(tournament_name: str, provided_location: str | None = None) -> tuple[str | None, bool, str | None]:
    """
    Resuelve la mejor ubicación meteorológica y si coincide con el calendario oficial.

    Returns:
        (ubicación, verificada_con_calendario, nota_sobre_discrepancia)
    """
    identity = normalize_tournament(tournament_name or provided_location or "")
    note = None

    if identity.official_name and identity.location:
        if provided_location:
            verified = locations_match(provided_location, identity.location)
            if not verified:
                note = (
                    f"La ubicación recibida ({provided_location}) no coincide con el calendario "
                    f"oficial ({identity.location}); se usa la ubicación oficial."
                )
            return identity.location, verified, note
        return identity.location, True, note

    resolved = identity.location or provided_location
    verified = bool(
        identity.location and provided_location and locations_match(provided_location, identity.location)
    )
    return resolved, verified, note


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

    known_report = _known_tournament_report(tournament_name, date)
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

