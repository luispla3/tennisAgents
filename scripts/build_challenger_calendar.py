"""Extrae el calendario ATP Challenger 2026 del PDF oficial a JSON."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = Path.home() / "Desktop" / "2026 ATP Challenger Tour Calenda - Perfect Tennis.pdf"
OUT_PATH = ROOT / "tennisAgents" / "data" / "atp_challenger_calendar_2026.json"

TIERS = {"50", "75", "100", "125", "175"}
DATE_RE = re.compile(r"(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{2}/\d{2})")
HEADER_RE = re.compile(
    r"^2026 ATP Challenger Tour Calenda.*$|^Tournament Category Location.*$|^Money$",
    re.MULTILINE,
)
NOISE_LINES = {
    "sgl",
    "dbl 16",
    "32 /",
    "outdoor",
    "indoor",
    "hard",
    "clay",
    "grass",
    "carpet",
}


def _clean_name(raw: str) -> str:
    name = " ".join(raw.split())
    name = re.sub(r"\s+Challenger\s*$", "", name, flags=re.IGNORECASE).strip()
    if not name.lower().endswith("challenger"):
        name = f"{name} Challenger"
    return name


def _normalize_key(name: str) -> str:
    import unicodedata

    text = unicodedata.normalize("NFKD", name)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\bchallenger\b", " ", text)
    return " ".join(text.split())


def parse_calendar(text: str) -> list[dict]:
    text = HEADER_RE.sub("", text)
    lines = [line.strip() for line in text.splitlines()]
    tournaments: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.lower() in TIERS:
            tier = int(line)
            j = i - 1
            while j >= 0 and (
                not lines[j]
                or lines[j].lower() in NOISE_LINES
                or lines[j].startswith("$")
                or lines[j].startswith("€")
            ):
                j -= 1
            if j < 0:
                i += 1
                continue

            name_parts: list[str] = []
            if lines[j].lower() == "challenger":
                j -= 1
                while j >= 0 and lines[j] and lines[j].lower() not in TIERS and not DATE_RE.search(lines[j]):
                    if lines[j].lower() not in NOISE_LINES and not lines[j].startswith("$") and not lines[j].startswith("€"):
                        name_parts.insert(0, lines[j])
                    j -= 1
            else:
                while j >= 0 and lines[j] and lines[j].lower() not in TIERS and not DATE_RE.search(lines[j]):
                    if lines[j].lower() not in NOISE_LINES and not lines[j].startswith("$") and not lines[j].startswith("€"):
                        name_parts.insert(0, lines[j])
                    j -= 1

            raw_name = " ".join(name_parts).strip()
            if not raw_name:
                i += 1
                continue

            k = i + 1
            location_parts: list[str] = []
            start = end = surface = None
            while k < len(lines):
                current = lines[k]
                if not current:
                    k += 1
                    continue
                if current.lower() in TIERS:
                    break
                date_match = DATE_RE.search(current)
                if date_match:
                    start, end = date_match.group(1), date_match.group(2)
                    before = current[: date_match.start()].strip(" ,")
                    if before:
                        location_parts.append(before)
                    surf = current[date_match.end() :].strip()
                    if surf:
                        surface = " ".join(surf.split())
                    k += 1
                    break
                if current.lower() in {"hard", "clay", "grass", "carpet"}:
                    surface = current
                    k += 1
                    continue
                if current.lower() in NOISE_LINES or current.startswith("$") or current.startswith("€"):
                    k += 1
                    continue
                location_parts.append(current)
                k += 1

            location = " ".join(location_parts).strip(" ,")
            name = _clean_name(raw_name)
            tournaments.append(
                {
                    "name": name,
                    "tier": tier,
                    "location": location or None,
                    "start": start,
                    "end": end,
                    "surface": surface,
                    "search_keys": sorted({_normalize_key(name), _normalize_key(raw_name)}),
                }
            )
            i = k
            continue
        i += 1
    return tournaments


def main() -> None:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    if not pdf_path.exists():
        raise SystemExit(f"PDF no encontrado: {pdf_path}")

    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    tournaments = parse_calendar(text)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "year": 2026,
        "source": "2026 ATP Challenger Tour Calendar - Perfect Tennis",
        "tournament_count": len(tournaments),
        "tournaments": tournaments,
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(tournaments)} tournaments to {OUT_PATH}")


if __name__ == "__main__":
    main()
