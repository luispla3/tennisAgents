"""Utilidades deterministas para consultar perfiles de Tennis Abstract."""

from __future__ import annotations

import re
import time
import unicodedata
from functools import lru_cache
from typing import Any

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.tennisabstract.com"
PLAYER_LIST_URL = f"{BASE_URL}/mwplayerlist.js"
PLAYER_URL = f"{BASE_URL}/cgi-bin/player.cgi"
JSFRAG_URL = f"{BASE_URL}/jsfrags/{{slug}}.js"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
SURFACE_ALIASES = {
    "clay": "Clay",
    "arcilla": "Clay",
    "tierra": "Clay",
    "tierra batida": "Clay",
    "hard": "Hard",
    "duro": "Hard",
    "grass": "Grass",
    "hierba": "Grass",
    "césped": "Grass",
    "cesped": "Grass",
}

_last_request_at = 0.0
_MIN_REQUEST_INTERVAL = 1.0


def _strip_accents(text: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _strip_accents(text).lower()).strip()


def _slug(full_name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", full_name)


def _is_initial_token(token: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z]\.?", token))


def _normalize_input_name(name: str) -> str:
    """Normaliza espacios y separa iniciales compactas tipo 'G.I.' -> 'G. I.'."""
    cleaned = " ".join(name.replace(",", " ").split())
    tokens: list[str] = []
    for token in cleaned.split():
        dotted = re.fullmatch(r"([A-Z])\.([A-Z])\.?", token)
        compact = re.fullmatch(r"([A-Z])([A-Z])\.?", token)
        if dotted:
            tokens.extend([f"{dotted.group(1)}.", f"{dotted.group(2)}."])
        elif compact and len(token) <= 3:
            tokens.extend([f"{compact.group(1)}.", f"{compact.group(2)}."])
        else:
            tokens.append(token)
    return " ".join(tokens)


def _split_initials_suffix(tokens: list[str]) -> tuple[list[str], list[str]] | None:
    """Separa apellido(s) e iniciales finales en formatos tipo 'Justo G. I.'."""
    if len(tokens) < 2:
        return None

    initials: list[str] = []
    index = len(tokens) - 1
    while index >= 0 and _is_initial_token(tokens[index]):
        initials.insert(0, tokens[index][0].lower())
        index -= 1

    if not initials or index < 0:
        return None

    surname_tokens = tokens[: index + 1]
    if not surname_tokens or any(_is_initial_token(token) for token in surname_tokens):
        return None

    return surname_tokens, initials


def _match_by_surname_and_initials(names: list[str], surname_tokens: list[str], initials: list[str]) -> str | None:
    surname_norm = _norm(" ".join(surname_tokens))
    surname_len = len(surname_tokens)
    candidates: list[str] = []

    for candidate in names:
        parts = candidate.split()
        if len(parts) <= surname_len:
            continue
        if _norm(" ".join(parts[-surname_len:])) != surname_norm:
            continue

        given_names = parts[: len(parts) - surname_len]
        if _initials_match_given(initials, given_names):
            candidates.append(candidate)

    return _pick_best_player_candidate(candidates)


def _initials_match_given(initials: list[str], given_names: list[str]) -> bool:
    if not initials:
        return True
    if len(initials) == 1:
        return any(name[:1].lower() == initials[0] for name in given_names)
    if len(given_names) < len(initials):
        return False
    return all(given_names[idx][:1].lower() == initial for idx, initial in enumerate(initials))


def _player_surname(parts: list[str]) -> str:
    return parts[-1] if parts else ""


def _player_given_names(parts: list[str]) -> list[str]:
    return parts[:-1] if len(parts) > 1 else []


def _rank_value(profile: dict[str, Any]) -> int:
    rank_raw = profile.get("current_rank")
    try:
        return int(str(rank_raw).replace(",", "").strip())
    except (TypeError, ValueError):
        return 10**9


def _try_profile_slug(input_name: str, candidate: str, slug: str) -> dict[str, Any] | None:
    url = f"{PLAYER_URL}?p={slug}"
    try:
        response = _get(url)
        profile = _profile_from_html(input_name, candidate, slug, url, response.text)
        if profile.get("found"):
            return profile
    except Exception:
        pass
    try:
        frag = _extract_player_frag(slug)
    except Exception:
        frag = ""
    if frag:
        return {
            "input_name": input_name,
            "resolved_name": candidate,
            "slug": slug,
            "found": True,
            "source": url,
            "profile_url": url,
            "current_rank": "N/D",
            "partial": True,
        }
    return None


def _pick_best_player_candidate(candidates: list[str], input_name: str = "") -> str | None:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    best_name: str | None = None
    best_rank = 10**9
    for candidate in candidates:
        profile = _try_profile_slug(input_name, candidate, _slug(candidate))
        if not profile:
            continue
        rank = _rank_value(profile)
        if rank < best_rank:
            best_rank = rank
            best_name = candidate

    return best_name or candidates[0]


def _search_player_list(name: str, names: list[str]) -> str | None:
    """Búsqueda difusa en el índice cuando el formato abreviado no encaja."""
    candidates = _search_player_list_all(name, names)
    return _pick_best_player_candidate(candidates, input_name=name)


def _search_player_list_all(name: str, names: list[str]) -> list[str]:
    tokens = name.split()
    if not tokens:
        return []

    has_initials = any(_is_initial_token(token) for token in tokens)
    trailing_surname = len(tokens) >= 2 and _is_initial_token(tokens[-1])
    initials = [token[0].lower() for token in tokens[1:] if _is_initial_token(token)]

    if trailing_surname:
        surname_parts = tokens[:-1]
    elif not has_initials and len(tokens) >= 2:
        surname_parts = tokens
    else:
        surname_parts = tokens[:1]

    surname_token = _norm(surname_parts[0]) if surname_parts else ""
    surname_norm = _norm(" ".join(surname_parts))

    candidates: list[str] = []
    for candidate in names:
        parts = candidate.split()
        if not parts:
            continue

        if trailing_surname or (not has_initials and len(tokens) >= 2):
            if len(parts) < len(surname_parts):
                continue
            if _norm(" ".join(parts[-len(surname_parts):])) != surname_norm:
                continue
            given = parts[: len(parts) - len(surname_parts)]
            if trailing_surname and initials and not _initials_match_given(initials, given):
                continue
        else:
            if surname_token and _norm(_player_surname(parts)) != surname_token and surname_token not in _norm(candidate):
                continue
            given = _player_given_names(parts)
            if initials and not _initials_match_given(initials, given):
                continue

        candidates.append(candidate)

    return candidates


def _slug_candidates(resolved_name: str, input_name: str) -> list[str]:
    """Genera slugs alternativos probando el nombre resuelto y coincidencias del índice."""
    candidates = [_slug(resolved_name)]
    for fuzzy in _search_player_list_all(_normalize_input_name(input_name), _player_names()):
        candidates.append(_slug(fuzzy))

    deduped: list[str] = []
    for slug in candidates:
        if slug and slug not in deduped:
            deduped.append(slug)
    return deduped


def _throttle() -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_at = time.monotonic()


def _get(url: str, retries: int = 4, allow_status: set[int] | None = None) -> requests.Response:
    last_error: Exception | None = None
    allowed = allow_status or set()
    for attempt in range(retries):
        _throttle()
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
            if response.status_code in allowed:
                return response
            if response.status_code == 429 and attempt < retries - 1:
                time.sleep(2.0 * (attempt + 1))
                continue
            response.raise_for_status()
            return response
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise last_error or RuntimeError(f"No se pudo obtener {url}")


@lru_cache(maxsize=1)
def _player_names() -> list[str]:
    response = _get(PLAYER_LIST_URL)
    return re.findall(r'"\(M\) ([^"]+)"', response.text)


def resolve_player_name(name: str) -> str:
    """Expande nombres abreviados tipo 'Faria J.' o 'Justo G. I.' usando Tennis Abstract."""
    cleaned = _normalize_input_name(name)
    normalized = _norm(cleaned)
    names = _player_names()

    for candidate in names:
        if _norm(candidate) == normalized:
            return candidate

    tokens = cleaned.split()

    split = _split_initials_suffix(tokens)
    if split:
        matched = _match_by_surname_and_initials(names, split[0], split[1])
        if matched:
            return matched

    if len(tokens) >= 2 and _is_initial_token(tokens[-1]):
        initial = tokens[-1][0].lower()
        surname_parts = tokens[:-1]
        surname_norm = _norm(" ".join(surname_parts))
        surname_len = len(surname_parts)
        trailing_matches: list[str] = []
        for candidate in names:
            parts = candidate.split()
            if len(parts) <= surname_len:
                continue
            if _norm(" ".join(parts[-surname_len:])) != surname_norm:
                continue
            given = _player_given_names(parts)
            if _initials_match_given([initial], given):
                trailing_matches.append(candidate)
        matched = _pick_best_player_candidate(trailing_matches, input_name=cleaned)
        if matched:
            return matched

    if len(tokens) >= 2 and _is_initial_token(tokens[0]):
        initial = tokens[0][0].lower()
        surname = _norm(" ".join(tokens[1:]))
        for candidate in names:
            parts = candidate.split()
            if not parts:
                continue
            if parts[0][:1].lower() == initial and _norm(" ".join(parts[1:])) == surname:
                return candidate

    fuzzy = _search_player_list(cleaned, names)
    if fuzzy:
        return fuzzy

    return cleaned


def _extract_var(html: str, name: str) -> str:
    match = re.search(rf"var {re.escape(name)} = ([^;]+);", html)
    if not match:
        return ""
    value = match.group(1).strip().strip("'").strip('"')
    return value


def _format_dob(raw_dob: str) -> str:
    if not raw_dob or not raw_dob.isdigit() or len(raw_dob) != 8:
        return raw_dob or "N/D"
    return f"{raw_dob[6:8]}-{raw_dob[4:6]}-{raw_dob[:4]}"


def _format_peak_date(raw_date: str) -> str:
    if not raw_date or not raw_date.isdigit() or len(raw_date) != 8:
        return raw_date or "N/D"
    return f"{raw_date[6:8]}-{raw_date[4:6]}-{raw_date[:4]}"


def _parse_table(table) -> list[dict[str, str]]:
    if table is None:
        return []

    header_cells = table.find("thead")
    headers: list[str] = []
    if header_cells:
        headers = [cell.get_text(" ", strip=True) for cell in header_cells.find_all("th")]
    if not headers:
        first_row = table.find("tr")
        if first_row:
            headers = [cell.get_text(" ", strip=True) for cell in first_row.find_all(["th", "td"])]

    rows: list[dict[str, str]] = []
    body_rows = table.find("tbody").find_all("tr") if table.find("tbody") else table.find_all("tr")[1:]
    for row in body_rows:
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
        if not cells:
            continue
        if not headers:
            rows.append({"values": " | ".join(cells)})
            continue
        padded = cells + [""] * max(0, len(headers) - len(cells))
        rows.append(dict(zip(headers, padded[: len(headers)])))
    return rows


def _extract_player_frag(slug: str) -> str:
    response = _get(JSFRAG_URL.format(slug=slug))
    match = re.search(r"var player_frag = `([\s\S]*?)`;", response.text)
    return match.group(1) if match else ""


def _normalize_surface(surface: str) -> str:
    return SURFACE_ALIASES.get(_norm(surface), surface.strip().title())


def _names_match(left: str, right: str) -> bool:
    left_norm = _norm(left)
    right_norm = _norm(right)
    if not left_norm or not right_norm:
        return False
    if left_norm == right_norm:
        return True
    left_tokens = left_norm.split()
    right_tokens = right_norm.split()
    if left_tokens and right_tokens and left_tokens[-1] == right_tokens[-1]:
        if left_tokens[0][:1] == right_tokens[0][:1]:
            return True
    return left_norm in right_norm or right_norm in left_norm


def _profile_from_html(name: str, resolved_name: str, slug: str, url: str, html: str) -> dict[str, Any]:
    fullname = _extract_var(html, "fullname")
    if not fullname:
        return {
            "input_name": name,
            "resolved_name": resolved_name,
            "found": False,
            "source": url,
            "slug": slug,
        }

    hand = {"R": "diestro", "L": "zurdo"}.get(_extract_var(html, "hand"), _extract_var(html, "hand") or "N/D")
    return {
        "input_name": name,
        "resolved_name": fullname,
        "slug": slug,
        "found": True,
        "source": url,
        "profile_url": url,
        "current_rank": _extract_var(html, "currentrank"),
        "peak_rank": _extract_var(html, "peakrank"),
        "peak_first": _format_peak_date(_extract_var(html, "peakfirst")),
        "elo_rating": _extract_var(html, "elo_rating"),
        "elo_rank": _extract_var(html, "elo_rank"),
        "country": _extract_var(html, "country"),
        "hand": hand,
        "height_cm": _extract_var(html, "ht"),
        "dob": _format_dob(_extract_var(html, "dob")),
        "twitter": _extract_var(html, "twitter"),
        "atp_id": _extract_var(html, "atp_id"),
    }


@lru_cache(maxsize=256)
def fetch_player_profile(name: str) -> dict[str, Any]:
    """Devuelve perfil básico ATP desde Tennis Abstract, si existe."""
    resolved_name = resolve_player_name(name)
    slug_candidates = _slug_candidates(resolved_name, name)
    errors: list[str] = []
    best_partial: dict[str, Any] | None = None

    for slug in slug_candidates:
        url = f"{PLAYER_URL}?p={slug}"
        try:
            response = _get(url)
            profile = _profile_from_html(name, resolved_name, slug, url, response.text)
            if profile.get("found"):
                return profile
        except Exception as exc:
            errors.append(f"{slug}: {exc}")
            try:
                frag = _extract_player_frag(slug)
            except Exception:
                frag = ""
            if frag:
                partial = {
                    "input_name": name,
                    "resolved_name": resolved_name,
                    "slug": slug,
                    "found": True,
                    "source": url,
                    "profile_url": url,
                    "current_rank": "N/D",
                    "peak_rank": "N/D",
                    "peak_first": "N/D",
                    "elo_rating": "N/D",
                    "elo_rank": "N/D",
                    "country": "N/D",
                    "hand": "N/D",
                    "height_cm": "N/D",
                    "dob": "N/D",
                    "twitter": "",
                    "atp_id": "",
                    "partial": True,
                    "warning": str(exc),
                }
                if best_partial is None:
                    best_partial = partial

    for candidate in _search_player_list_all(_normalize_input_name(name), _player_names()):
        profile = _try_profile_slug(name, candidate, _slug(candidate))
        if profile and profile.get("found") and not profile.get("partial"):
            return profile

    if best_partial:
        return best_partial

    return {
        "input_name": name,
        "resolved_name": resolved_name,
        "found": False,
        "source": f"{PLAYER_URL}?p={slug_candidates[0]}",
        "tried_slugs": slug_candidates,
        "error": "; ".join(errors) if errors else "Perfil no encontrado",
    }


@lru_cache(maxsize=256)
def fetch_player_data(name: str) -> dict[str, Any]:
    """Perfil + tablas parseadas desde jsfrags/{slug}.js."""
    profile = fetch_player_profile(name)
    if not profile.get("found"):
        return profile

    slug = profile["slug"]
    frag = _extract_player_frag(slug)
    soup = BeautifulSoup(frag, "html.parser")

    return {
        **profile,
        "recent_matches": _parse_table(soup.find("table", id="recent-results")),
        "career_splits": _parse_table(soup.find("table", id="career-splits")),
        "last52_splits": _parse_table(soup.find("table", id="last52-splits")),
        "head_to_heads": _parse_table(soup.find("table", id="head-to-heads")),
        "tour_seasons": _parse_table(soup.find("table", id="tour-years")),
        "jsfrag_source": JSFRAG_URL.format(slug=slug),
    }


def _find_head_to_head(player_data: dict[str, Any], opponent_name: str) -> dict[str, str] | None:
    resolved_opponent = resolve_player_name(opponent_name)
    for row in player_data.get("head_to_heads", []):
        opponent_cell = row.get("Opponent", "")
        opponent_clean = re.sub(r"\[[A-Z]{3}\]", "", opponent_cell).strip()
        if _names_match(resolved_opponent, opponent_clean):
            return row
    return None


def _find_surface_split(rows: list[dict[str, str]], surface: str) -> dict[str, str] | None:
    target = _normalize_surface(surface)
    for row in rows:
        if row.get("Split", "").strip().lower() == target.lower():
            return row
    return None


def _parse_numeric_pct(value: str) -> float | None:
    if not value or value.strip().upper() in {"N/D", "N/A", "-"}:
        return None
    try:
        return float(value.replace("%", "").strip())
    except ValueError:
        return None


def _match_summary(row: dict[str, str]) -> str:
    return row.get("", row.get("Match", "")).strip()


def _is_upcoming_match(row: dict[str, str]) -> bool:
    summary = _match_summary(row)
    score = (row.get("Score") or "").strip()
    if " vs " in summary and " d. " not in summary:
        return True
    return not score


def _match_result_won(row: dict[str, str], player_name: str) -> bool | None:
    summary = _match_summary(row)
    if " d. " not in summary:
        return None
    winner = re.sub(r"^\([^)]*\)\s*", "", summary.split(" d. ", 1)[0])
    winner = re.sub(r"^\d+\)\s*", "", winner).strip()
    return _names_match(player_name, winner)


def _format_surface_from_recent(data: dict[str, Any], surface: str, limit: int = 20) -> str | None:
    """Deriva métricas de superficie desde recent-results cuando no hay career-splits."""
    normalized = _normalize_surface(surface)
    rows = [
        row for row in data.get("recent_matches", [])
        if _normalize_surface(row.get("Surface", "")) == normalized
        and not _is_upcoming_match(row)
    ][:limit]
    if not rows:
        return None

    wins = losses = 0
    stat_samples: dict[str, list[float]] = {"A%": [], "1stIn": [], "1st%": [], "2nd%": []}
    for row in rows:
        result = _match_result_won(row, data["resolved_name"])
        if result is True:
            wins += 1
        elif result is False:
            losses += 1
        for key in stat_samples:
            value = _parse_numeric_pct(row.get(key, ""))
            if value is not None:
                stat_samples[key].append(value)

    total = wins + losses
    winrate = f"{wins / total * 100:.1f}%" if total else "N/D"

    def _avg(key: str) -> str:
        values = stat_samples[key]
        return f"{sum(values) / len(values):.1f}%" if values else "N/D"

    return "\n".join([
        f"## Rendimiento en {normalized} (Tennis Abstract — derivado de partidos recientes)",
        f"- Jugador: {data['resolved_name']}",
        f"- Fuente: {data['jsfrag_source']}",
        "- Nota: no hay split de carrera en Tennis Abstract; métricas calculadas desde recent-results.",
        "",
        "### Muestra reciente en la superficie",
        f"- Partidos con resultado considerados: {len(rows)}",
        f"- Récord en la muestra: {wins}W-{losses}L (winrate {winrate})",
        f"- Aces (A%): {_avg('A%')}",
        f"- Primer servicio in (1stIn): {_avg('1stIn')}",
        f"- Puntos ganados con 1er servicio (1st%): {_avg('1st%')}",
        f"- Puntos ganados con 2o servicio (2nd%): {_avg('2nd%')}",
        "",
    ]).strip()


def format_profiles_report(player1_name: str, player2_name: str) -> str:
    profiles = []
    for player_name in (player1_name, player2_name):
        try:
            profiles.append(fetch_player_profile(player_name))
        except Exception as exc:
            profiles.append({
                "input_name": player_name,
                "resolved_name": player_name,
                "found": False,
                "source": PLAYER_URL,
                "error": str(exc),
            })

    if not any(profile.get("found") for profile in profiles):
        return ""

    lines = ["## Perfiles Tennis Abstract (fuente determinista)", ""]
    for profile in profiles:
        if not profile.get("found"):
            lines.extend([
                f"### {profile['input_name']}",
                "- Perfil no encontrado en Tennis Abstract.",
                f"- Fuente consultada: {profile['source']}",
                f"- Error: {profile.get('error', 'N/D')}" if profile.get("error") else "",
                "",
            ])
            continue

        lines.extend([
            f"### {profile['resolved_name']}",
            f"- Nombre original recibido: {profile['input_name']}",
            f"- País: {profile.get('country') or 'N/D'}",
            f"- Ranking ATP actual: {profile.get('current_rank') or 'N/D'}",
            f"- Mejor ranking ATP: {profile.get('peak_rank') or 'N/D'} ({profile.get('peak_first') or 'fecha N/D'})",
            f"- Elo Tennis Abstract: {profile.get('elo_rating') or 'N/D'} (rank Elo: {profile.get('elo_rank') or 'N/D'})",
            f"- Mano: {profile.get('hand') or 'N/D'}",
            f"- Altura: {profile.get('height_cm') or 'N/D'} cm",
            f"- Fecha nacimiento: {profile.get('dob') or 'N/D'}",
            f"- Fuente: {profile['source']}",
            "",
        ])

    return "\n".join(line for line in lines if line is not None).strip()


def format_player_identity_block(player1_name: str, player2_name: str) -> str:
    """Bloque compacto de país/perfil verificado para prompts de analistas."""
    lines = ["## Identidad verificada de jugadores (Tennis Abstract)", ""]
    found_any = False

    for player_name in (player1_name, player2_name):
        try:
            profile = fetch_player_profile(player_name)
        except Exception as exc:
            lines.extend([
                f"### {player_name}",
                f"- País: N/D (error al consultar Tennis Abstract: {exc})",
                "",
            ])
            continue

        if not profile.get("found"):
            lines.extend([
                f"### {player_name}",
                "- País: N/D (perfil no encontrado en Tennis Abstract)",
                "",
            ])
            continue

        found_any = True
        lines.extend([
            f"### {profile['resolved_name']}",
            f"- País: {profile.get('country') or 'N/D'}",
            f"- Mano: {profile.get('hand') or 'N/D'}",
            f"- Ranking ATP: {profile.get('current_rank') or 'N/D'}",
            f"- Fuente: Tennis Abstract",
            "",
        ])

    if not found_any:
        return ""

    lines.append(
        "Obligatorio: usa EXCLUSIVAMENTE estos países verificados; "
        "no infieras nacionalidad por el nombre del jugador."
    )
    return "\n".join(lines).strip()


def format_recent_matches_report(player1_name: str, player2_name: str, num_matches: int = 30) -> str:
    sections: list[str] = ["## Partidos recientes (Tennis Abstract)", ""]
    found_any = False

    for player_name in (player1_name, player2_name):
        try:
            data = fetch_player_data(player_name)
        except Exception as exc:
            sections.extend([
                f"### {player_name}",
                f"- Error al consultar Tennis Abstract: {exc}",
                "",
            ])
            continue

        if not data.get("found"):
            sections.extend([
                f"### {player_name}",
                "- Perfil no encontrado en Tennis Abstract.",
                "",
            ])
            continue

        found_any = True
        matches = data.get("recent_matches", [])[:num_matches]
        sections.append(f"### {data['resolved_name']}")
        sections.append(f"- Fuente: {data['jsfrag_source']}")
        if not matches:
            sections.extend(["- No hay partidos recientes disponibles.", ""])
            continue

        sections.append("")
        sections.append("| Fecha | Torneo | Superficie | Ronda | Resultado | Marcador | A% | 1stIn | 1st% | 2nd% |")
        sections.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for match in matches:
            sections.append(
                "| {date} | {tournament} | {surface} | {round_} | {summary} | {score} | {aces} | {first_in} | {first_pct} | {second_pct} |".format(
                    date=match.get("Date", "N/D"),
                    tournament=match.get("Tournament", "N/D"),
                    surface=match.get("Surface", "N/D"),
                    round_=match.get("Rd", "N/D"),
                    summary=match.get("", match.get("Match", "N/D")),
                    score=match.get("Score", "N/D"),
                    aces=match.get("A%", "N/D"),
                    first_in=match.get("1stIn", "N/D"),
                    first_pct=match.get("1st%", "N/D"),
                    second_pct=match.get("2nd%", "N/D"),
                )
            )
        sections.append("")

    return "\n".join(sections).strip() if found_any else ""


def format_surface_report(player_name: str, surface: str) -> str:
    try:
        data = fetch_player_data(player_name)
    except Exception as exc:
        return f"Error al consultar Tennis Abstract para {player_name}: {exc}"

    if not data.get("found"):
        return f"No se encontró perfil en Tennis Abstract para {player_name}."

    normalized_surface = _normalize_surface(surface)
    career = _find_surface_split(data.get("career_splits", []), normalized_surface)
    last52 = _find_surface_split(data.get("last52_splits", []), normalized_surface)

    if not career and not last52:
        fallback = _format_surface_from_recent(data, normalized_surface)
        if fallback:
            return fallback
        return (
            f"No hay estadísticas de superficie `{normalized_surface}` en Tennis Abstract "
            f"para {data['resolved_name']}."
        )

    lines = [
        f"## Rendimiento en {normalized_surface} (Tennis Abstract)",
        f"- Jugador: {data['resolved_name']} (entrada: {player_name})",
        f"- Fuente: {data['jsfrag_source']}",
        "",
    ]
    if not career and last52:
        lines.extend([
            "- Nota: no hay split de carrera en Tennis Abstract; usar métricas de últimas 52 semanas.",
            "",
        ])

    def _append_split(title: str, row: dict[str, str] | None) -> None:
        if not row:
            lines.append(f"### {title}")
            lines.append("- No disponible.")
            lines.append("")
            return
        lines.extend([
            f"### {title}",
            f"- Partidos: {row.get('M', 'N/D')} ({row.get('W', 'N/D')}W-{row.get('L', 'N/D')}L)",
            f"- Winrate: {row.get('Win%', 'N/D')}",
            f"- Sets: {row.get('Set W-L', 'N/D')} ({row.get('Set%', 'N/D')})",
            f"- Juegos: {row.get('Game W-L', 'N/D')} ({row.get('Game%', 'N/D')})",
            f"- Aces (A%): {row.get('A%', 'N/D')}",
            f"- Dobles faltas (DF%): {row.get('DF%', 'N/D')}",
            f"- Primer servicio in (1stIn): {row.get('1stIn', 'N/D')}",
            f"- Puntos ganados con 1er servicio (1st%): {row.get('1st%', 'N/D')}",
            f"- Puntos ganados con 2o servicio (2nd%): {row.get('2nd%', 'N/D')}",
            f"- Juegos de servicio ganados (Hld%): {row.get('Hld%', 'N/D')}",
            f"- Break points convertidos (Brk%): {row.get('Brk%', 'N/D')}",
            f"- Puntos ganados al servicio (SPW): {row.get('SPW', 'N/D')}",
            f"- Puntos ganados al resto (RPW): {row.get('RPW', 'N/D')}",
            "",
        ])

    _append_split("Carrera en la superficie", career)
    _append_split("Últimas 52 semanas en la superficie", last52)
    return "\n".join(lines).strip()


def _find_recent_h2h(player_data: dict[str, Any], opponent_name: str) -> list[dict[str, str]]:
    resolved_opponent = resolve_player_name(opponent_name)
    matches: list[dict[str, str]] = []
    for row in player_data.get("recent_matches", []):
        summary = row.get("", "")
        if _names_match(resolved_opponent, summary):
            matches.append(row)
    return matches


def format_head_to_head_report(player1_name: str, player2_name: str) -> str:
    sections: list[str] = ["## Head-to-head (Tennis Abstract)", ""]
    found = False

    for player_name, opponent_name in ((player1_name, player2_name), (player2_name, player1_name)):
        try:
            data = fetch_player_data(player_name)
        except Exception as exc:
            sections.append(f"- Error consultando {player_name}: {exc}")
            continue

        if not data.get("found"):
            continue

        row = _find_head_to_head(data, opponent_name)
        if row:
            found = True
            opponent = re.sub(r"\[[A-Z]{3}\]", "", row.get("Opponent", resolve_player_name(opponent_name))).strip()
            sections.extend([
                f"### {data['resolved_name']} vs {opponent}",
                f"- Enfrentamientos: {row.get('Mtgs', 'N/D')}",
                f"- Marcador: {row.get('W', 'N/D')}-{row.get('L', 'N/D')} a favor de {data['resolved_name']}",
                f"- Winrate: {row.get('Win%', 'N/D')}",
                f"- Tie-breaks: {row.get('TB', 'N/D')} ({row.get('TB%', 'N/D')})",
                f"- Primer enfrentamiento: {row.get('First', 'N/D')}",
                f"- Último enfrentamiento: {row.get('Last', 'N/D')}",
                f"- Aces (A%): {row.get('A%', 'N/D')}",
                f"- Primer servicio in (1stIn): {row.get('1stIn', 'N/D')}",
                f"- Puntos ganados con 1er servicio (1st%): {row.get('1st%', 'N/D')}",
                f"- Puntos ganados con 2o servicio (2nd%): {row.get('2nd%', 'N/D')}",
                f"- Fuente: {data['jsfrag_source']}",
                "",
            ])
            break

        recent = _find_recent_h2h(data, opponent_name)
        if recent:
            found = True
            opponent = resolve_player_name(opponent_name)
            sections.extend([
                f"### {data['resolved_name']} vs {opponent}",
                "- Historial H2H agregado: no disponible en Tennis Abstract.",
                f"- Enfrentamientos detectados en resultados recientes: {len(recent)}",
                f"- Fuente: {data['jsfrag_source']}",
                "",
                "| Fecha | Torneo | Superficie | Resultado | Marcador |",
                "| --- | --- | --- | --- | --- |",
            ])
            for match in recent:
                sections.append(
                    "| {date} | {tournament} | {surface} | {summary} | {score} |".format(
                        date=match.get("Date", "N/D"),
                        tournament=match.get("Tournament", "N/D"),
                        surface=match.get("Surface", "N/D"),
                        summary=match.get("", "N/D"),
                        score=match.get("Score", "N/D"),
                    )
                )
            sections.append("")
            break

    if not found:
        p1 = resolve_player_name(player1_name)
        p2 = resolve_player_name(player2_name)
        return (
            "## Head-to-head (Tennis Abstract)\n\n"
            f"No hay historial H2H confirmado entre `{p1}` y `{p2}` en Tennis Abstract."
        )

    return "\n".join(sections).strip()
