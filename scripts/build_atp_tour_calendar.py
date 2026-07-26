"""Genera el calendario ATP Tour 2026 (superior a Challenger) desde el PDF + nombres canónicos."""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = Path.home() / "Desktop" / "2026-atp-tour-calendar-december-2025.pdf"
OUT_PATH = ROOT / "tennisAgents" / "data" / "atp_tour_calendar_2026.json"

# Nombres canónicos extraídos del calendario ATP Tour 2026 (edición diciembre 2025).
CANONICAL_TOURNAMENTS: tuple[dict[str, str | list[str]], ...] = (
    {"name": "United Cup", "category": "united_cup", "month": "JAN", "search_keys": ["united cup", "perth", "sydney"]},
    {"name": "Brisbane International", "category": "atp_250", "month": "JAN", "search_keys": ["brisbane international", "brisbane"]},
    {"name": "Hong Kong Tennis Open", "category": "atp_250", "month": "JAN", "search_keys": ["hong kong tennis", "hong kong"]},
    {"name": "ASB Classic", "category": "atp_250", "month": "JAN", "search_keys": ["asb classic", "auckland"]},
    {"name": "Adelaide International", "category": "atp_250", "month": "JAN", "search_keys": ["adelaide international", "adelaide"]},
    {"name": "Australian Open", "category": "grand_slam", "month": "JAN", "search_keys": ["australian open", "melbourne"]},
    {"name": "Davis Cup Qualifiers 1st Round", "category": "davis_cup", "month": "FEB", "search_keys": ["davis cup qualifiers", "davis cup 1st"]},
    {"name": "Open Occitanie Montpellier", "category": "atp_250", "month": "FEB", "search_keys": ["montpellier", "occitanie"]},
    {"name": "ABN AMRO Open", "category": "atp_500", "month": "FEB", "search_keys": ["abn amro", "rotterdam"]},
    {"name": "Dallas Open", "category": "atp_500", "month": "FEB", "search_keys": ["dallas open", "dallas"]},
    {"name": "Qatar ExxonMobil Open", "category": "atp_250", "month": "FEB", "search_keys": ["qatar exxonmobil", "doha"]},
    {"name": "Argentina Open", "category": "atp_250", "month": "FEB", "search_keys": ["argentina open", "buenos aires"]},
    {"name": "Rio Open", "category": "atp_500", "month": "FEB", "search_keys": ["rio open", "rio de janeiro"]},
    {"name": "Delray Beach Open", "category": "atp_250", "month": "FEB", "search_keys": ["delray beach"]},
    {"name": "Dubai Duty Free Tennis Championships", "category": "atp_500", "month": "FEB", "search_keys": ["dubai duty free", "dubai"]},
    {"name": "Chile Open", "category": "atp_250", "month": "FEB", "search_keys": ["chile open", "santiago", "bci seguros"]},
    {"name": "Abierto Mexicano Telcel", "category": "atp_500", "month": "FEB", "search_keys": ["acapulco", "mexicano telcel"]},
    {"name": "BNP Paribas Open", "category": "masters_1000", "month": "MAR", "search_keys": ["indian wells", "bnp paribas open"]},
    {"name": "Miami Open", "category": "masters_1000", "month": "MAR", "search_keys": ["miami open", "miami"]},
    {"name": "U.S. Men's Clay Court Championship", "category": "atp_250", "month": "MAR", "search_keys": ["houston", "clay court championship"]},
    {"name": "Tiriac Open", "category": "atp_250", "month": "MAR", "search_keys": ["tiriac open", "bucharest"]},
    {"name": "Grand Prix Hassan II", "category": "atp_250", "month": "MAR", "search_keys": ["hassan ii", "marrakech"]},
    {"name": "Rolex Monte-Carlo Masters", "category": "masters_1000", "month": "APR", "search_keys": ["monte carlo", "monte-carlo"]},
    {"name": "Barcelona Open Banc Sabadell", "category": "atp_500", "month": "APR", "search_keys": ["barcelona open", "banc sabadell"]},
    {"name": "BMW Open", "category": "atp_500", "month": "APR", "search_keys": ["bmw open", "munich"]},
    {"name": "Mutua Madrid Open", "category": "masters_1000", "month": "APR", "search_keys": ["mutua madrid", "madrid open"]},
    {"name": "Internazionali BNL d'Italia", "category": "masters_1000", "month": "MAY", "search_keys": ["internazionali bnl", "rome", "italia"]},
    {"name": "Gonet Geneva Open", "category": "atp_250", "month": "MAY", "search_keys": ["geneva open", "geneva"]},
    {"name": "Bitpanda Hamburg Open", "category": "atp_500", "month": "MAY", "search_keys": ["hamburg open", "hamburg"]},
    {"name": "Roland Garros", "category": "grand_slam", "month": "MAY", "search_keys": ["roland garros", "french open", "paris"]},
    {"name": "Boss Open", "category": "atp_250", "month": "JUN", "search_keys": ["boss open", "stuttgart"]},
    {"name": "Libema Open", "category": "atp_250", "month": "JUN", "search_keys": ["libema open", "s-hertogenbosch", "hertogenbosch"]},
    {"name": "HSBC Championships", "category": "atp_500", "month": "JUN", "search_keys": ["hsbc championships", "queens", "queen's"]},
    {"name": "Terra Wortmann Open", "category": "atp_500", "month": "JUN", "search_keys": ["terra wortmann", "halle"]},
    {"name": "Lexus Eastbourne Open", "category": "atp_250", "month": "JUN", "search_keys": ["eastbourne"]},
    {"name": "Mallorca Championships", "category": "atp_250", "month": "JUN", "search_keys": ["mallorca"]},
    {"name": "The Championships Wimbledon", "category": "grand_slam", "month": "JUN", "search_keys": ["wimbledon", "championships wimbledon"]},
    {"name": "Nordea Open", "category": "atp_250", "month": "JUL", "search_keys": ["nordea open", "bastad", "båstad"]},
    {"name": "Swiss Open Gstaad", "category": "atp_250", "month": "JUL", "search_keys": ["swiss open", "gstaad"]},
    {"name": "Millennium Estoril Open", "category": "atp_250", "month": "JUL", "search_keys": ["estoril open", "estoril"]},
    {"name": "Plava Laguna Croatia Open Umag", "category": "atp_250", "month": "JUL", "search_keys": ["croatia open", "umag"]},
    {"name": "Generali Open", "category": "atp_250", "month": "JUL", "search_keys": ["generali open", "kitzbuhel"]},
    {"name": "Mubadala Citi DC Open", "category": "atp_500", "month": "JUL", "search_keys": ["citi dc open", "washington"]},
    {"name": "Los Cabos Open", "category": "atp_250", "month": "JUL", "search_keys": ["los cabos"]},
    {"name": "Mifel Tennis Open", "category": "atp_250", "month": "JUL", "search_keys": ["mifel tennis"]},
    {"name": "National Bank Open", "category": "masters_1000", "month": "AUG", "search_keys": ["national bank open", "montreal", "rogers"]},
    {"name": "Cincinnati Open", "category": "masters_1000", "month": "AUG", "search_keys": ["cincinnati open", "cincinnati"]},
    {"name": "Winston-Salem Open", "category": "atp_250", "month": "AUG", "search_keys": ["winston salem"]},
    {"name": "US Open", "category": "grand_slam", "month": "AUG", "search_keys": ["us open", "new york", "flushing"]},
    {"name": "Chengdu Open", "category": "atp_250", "month": "SEP", "search_keys": ["chengdu open", "chengdu"]},
    {"name": "Hangzhou Open", "category": "atp_250", "month": "SEP", "search_keys": ["hangzhou open", "hangzhou", "lynk co"]},
    {"name": "Davis Cup Qualifiers 2nd Round", "category": "davis_cup", "month": "SEP", "search_keys": ["davis cup qualifiers 2"]},
    {"name": "Laver Cup", "category": "laver_cup", "month": "SEP", "search_keys": ["laver cup"]},
    {"name": "Japan Open Tennis Championships", "category": "atp_500", "month": "SEP", "search_keys": ["japan open", "tokyo", "kinoshita"]},
    {"name": "China Open", "category": "atp_500", "month": "SEP", "search_keys": ["china open", "beijing"]},
    {"name": "Rolex Shanghai Masters", "category": "masters_1000", "month": "OCT", "search_keys": ["shanghai masters", "shanghai"]},
    {"name": "European Open", "category": "atp_250", "month": "OCT", "search_keys": ["european open", "brussels", "bnpp fortis"]},
    {"name": "Swiss Indoors Basel", "category": "atp_500", "month": "OCT", "search_keys": ["swiss indoors", "basel"]},
    {"name": "Almaty Open", "category": "atp_250", "month": "OCT", "search_keys": ["almaty open", "almaty"]},
    {"name": "Erste Bank Open", "category": "atp_500", "month": "OCT", "search_keys": ["erste bank open", "vienna"]},
    {"name": "Rolex Paris Masters", "category": "masters_1000", "month": "NOV", "search_keys": ["paris masters", "rolex paris"]},
    {"name": "BNP Paribas Nordic Open", "category": "atp_250", "month": "NOV", "search_keys": ["nordic open", "stockholm"]},
    {"name": "Nitto ATP Finals", "category": "atp_finals", "month": "NOV", "search_keys": ["nitto atp finals", "atp finals", "turin"]},
    {"name": "Davis Cup Finals", "category": "davis_cup", "month": "NOV", "search_keys": ["davis cup finals"]},
    {"name": "Next Gen ATP Finals", "category": "next_gen", "month": "DEC", "search_keys": ["next gen atp finals", "next gen"]},
)

CANONICAL_LOCATIONS: dict[str, str] = {
    "United Cup": "Perth, Australia",
    "Brisbane International": "Brisbane, Australia",
    "Hong Kong Tennis Open": "Hong Kong, China",
    "ASB Classic": "Auckland, New Zealand",
    "Adelaide International": "Adelaide, Australia",
    "Australian Open": "Melbourne, Australia",
    "Open Occitanie Montpellier": "Montpellier, France",
    "ABN AMRO Open": "Rotterdam, Netherlands",
    "Dallas Open": "Dallas, United States",
    "Qatar ExxonMobil Open": "Doha, Qatar",
    "Argentina Open": "Buenos Aires, Argentina",
    "Rio Open": "Rio de Janeiro, Brazil",
    "Delray Beach Open": "Delray Beach, United States",
    "Dubai Duty Free Tennis Championships": "Dubai, United Arab Emirates",
    "Chile Open": "Santiago, Chile",
    "Abierto Mexicano Telcel": "Acapulco, Mexico",
    "BNP Paribas Open": "Indian Wells, United States",
    "Miami Open": "Miami, United States",
    "U.S. Men's Clay Court Championship": "Houston, United States",
    "Tiriac Open": "Bucharest, Romania",
    "Grand Prix Hassan II": "Marrakech, Morocco",
    "Rolex Monte-Carlo Masters": "Monte Carlo, Monaco",
    "Barcelona Open Banc Sabadell": "Barcelona, Spain",
    "BMW Open": "Munich, Germany",
    "Mutua Madrid Open": "Madrid, Spain",
    "Internazionali BNL d'Italia": "Rome, Italy",
    "Gonet Geneva Open": "Geneva, Switzerland",
    "Bitpanda Hamburg Open": "Hamburg, Germany",
    "Roland Garros": "Paris, France",
    "Boss Open": "Stuttgart, Germany",
    "Libema Open": "'s-Hertogenbosch, Netherlands",
    "HSBC Championships": "London, United Kingdom",
    "Terra Wortmann Open": "Halle, Germany",
    "Lexus Eastbourne Open": "Eastbourne, United Kingdom",
    "Mallorca Championships": "Mallorca, Spain",
    "The Championships Wimbledon": "London, United Kingdom",
    "Nordea Open": "Bastad, Sweden",
    "Swiss Open Gstaad": "Gstaad, Switzerland",
    "Millennium Estoril Open": "Estoril, Portugal",
    "Plava Laguna Croatia Open Umag": "Umag, Croatia",
    "Generali Open": "Kitzbuhel, Austria",
    "Mubadala Citi DC Open": "Washington, D.C., United States",
    "Los Cabos Open": "Los Cabos, Mexico",
    "Mifel Tennis Open": "Los Cabos, Mexico",
    "National Bank Open": "Montreal, Canada",
    "Cincinnati Open": "Cincinnati, United States",
    "Winston-Salem Open": "Winston-Salem, United States",
    "US Open": "New York, United States",
    "Chengdu Open": "Chengdu, China",
    "Hangzhou Open": "Hangzhou, China",
    "Laver Cup": "London, United Kingdom",
    "Japan Open Tennis Championships": "Tokyo, Japan",
    "China Open": "Beijing, China",
    "Rolex Shanghai Masters": "Shanghai, China",
    "European Open": "Brussels, Belgium",
    "Swiss Indoors Basel": "Basel, Switzerland",
    "Almaty Open": "Almaty, Kazakhstan",
    "Erste Bank Open": "Vienna, Austria",
    "Rolex Paris Masters": "Paris, France",
    "BNP Paribas Nordic Open": "Stockholm, Sweden",
    "Nitto ATP Finals": "Turin, Italy",
}

CANONICAL_SURFACES: dict[str, str] = {
    "Australian Open": "hard",
    "BNP Paribas Open": "hard",
    "Miami Open": "hard",
    "U.S. Men's Clay Court Championship": "clay",
    "Tiriac Open": "clay",
    "Grand Prix Hassan II": "clay",
    "Rolex Monte-Carlo Masters": "clay",
    "Barcelona Open Banc Sabadell": "clay",
    "BMW Open": "clay",
    "Mutua Madrid Open": "clay",
    "Internazionali BNL d'Italia": "clay",
    "Gonet Geneva Open": "clay",
    "Bitpanda Hamburg Open": "clay",
    "Roland Garros": "clay",
    "Boss Open": "grass",
    "Libema Open": "grass",
    "HSBC Championships": "grass",
    "Terra Wortmann Open": "grass",
    "Lexus Eastbourne Open": "grass",
    "Mallorca Championships": "grass",
    "The Championships Wimbledon": "grass",
    "Nordea Open": "clay",
    "Swiss Open Gstaad": "clay",
    "Millennium Estoril Open": "clay",
    "Plava Laguna Croatia Open Umag": "clay",
    "Generali Open": "clay",
    "US Open": "hard",
}

CATEGORY_LABELS = {
    "masters_1000": "ATP Masters 1000",
    "grand_slam": "Grand Slam",
    "atp_500": "ATP 500",
    "atp_250": "ATP 250",
    "atp_finals": "ATP Finals",
    "next_gen": "Next Gen ATP Finals",
    "davis_cup": "Davis Cup",
    "laver_cup": "Laver Cup",
    "united_cup": "United Cup",
}

CATEGORY_PDF_MARKERS = {
    "masters_1000": ("MASTERS 1000",),
    "grand_slam": ("GRAND SLAM",),
    "atp_500": ("ATP 500",),
    "atp_250": ("ATP 250",),
    "atp_finals": ("ATP FINALS", "NITTO"),
    "next_gen": ("NEXT GEN",),
    "davis_cup": ("DAVIS CUP",),
    "laver_cup": ("LAVER CUP",),
    "united_cup": ("UNITED CUP",),
}


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _normalize_pdf_text(text: str) -> str:
    text = text.replace("\u2019", "'").replace("\ufffd", " ")
    text = _strip_accents(text)
    text = re.sub(r"\bA\s+TP\b", "ATP", text, flags=re.I)
    text = re.sub(r"\bHA\s+TP\b", "H ATP", text, flags=re.I)
    text = re.sub(r"\bCLA\s+TP\b", "CL ATP", text, flags=re.I)
    text = re.sub(r"\bIHATP\b", "H ATP", text, flags=re.I)
    text = re.sub(r"\bIHA\s+TP\b", "H ATP", text, flags=re.I)
    return text.upper()


def _normalize_key(text: str) -> str:
    text = _strip_accents(str(text or "")).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def build_payload(pdf_text: str | None = None) -> dict:
    tournaments = []
    for item in CANONICAL_TOURNAMENTS:
        keys = {_normalize_key(item["name"])}
        for key in item.get("search_keys") or []:
            keys.add(_normalize_key(key))
        tournaments.append(
            {
                "name": item["name"],
                "category": item["category"],
                "category_label": CATEGORY_LABELS[str(item["category"])],
                "month": item.get("month"),
                "location": item.get("location") or CANONICAL_LOCATIONS.get(str(item["name"])),
                "surface": item.get("surface") or CANONICAL_SURFACES.get(str(item["name"])),
                "search_keys": sorted(k for k in keys if k),
            }
        )

    warnings: list[str] = []
    if pdf_text:
        normalized_pdf = _normalize_pdf_text(pdf_text)
        for item in tournaments:
            markers = CATEGORY_PDF_MARKERS.get(str(item["category"]), ())
            if markers and not any(marker in normalized_pdf for marker in markers):
                warnings.append(f"Categoría no encontrada en PDF: {item['name']} ({item['category']})")
            found = any(_normalize_key(key) in _normalize_key(normalized_pdf) for key in item.get("search_keys") or [])
            if not found and _normalize_key(str(item["name"])) not in _normalize_key(normalized_pdf):
                warnings.append(f"Nombre no localizado claramente en PDF: {item['name']}")

    payload = {
        "year": 2026,
        "source": "2026 ATP Tour Calendar (December 2025 edition)",
        "tournament_count": len(tournaments),
        "tournaments": tournaments,
    }
    if warnings:
        payload["pdf_validation_warnings"] = warnings
    return payload


def main() -> None:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    pdf_text = None
    if pdf_path.exists():
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif len(sys.argv) > 1:
        raise SystemExit(f"PDF no encontrado: {pdf_path}")

    payload = build_payload(pdf_text)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {payload['tournament_count']} tournaments to {OUT_PATH}")
    for warning in payload.get("pdf_validation_warnings") or []:
        print(f"  warning: {warning}")


if __name__ == "__main__":
    main()
