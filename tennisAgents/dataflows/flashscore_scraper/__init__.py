"""Scraper de Flashscore: partidos en vivo y estadísticas."""

from .client import FlashscoreClient, FlashscoreError, SPORT_IDS
from .parser import (
    build_finished_results,
    dedupe_matches,
    filter_matches,
    has_decisive_score,
    is_finished_tennis_match,
    merge_player_feed_index,
    parse_dc_score,
    parse_feed,
    parse_scoreboard_feed,
    parse_stats,
    _parse_cells,
    _split_rows,
)

__all__ = [
    "FlashscoreClient",
    "FlashscoreError",
    "SPORT_IDS",
    "filter_matches",
    "parse_feed",
    "parse_stats",
    "get_live_matches",
    "get_matches",
    "get_finished_matches",
    "get_match_statistics",
]

__version__ = "1.0.0"


def get_matches(
    sport: str = "tennis",
    day_offset: int = 0,
    locale: str = "es",
    live_only: bool = False,
) -> list[dict]:
    """Obtiene partidos del día para un deporte."""
    client = FlashscoreClient(locale=locale)
    sport_id = client.sport_id(sport)
    feed = client.get_daily_feed(sport_id=sport_id, day_offset=day_offset)
    matches = parse_feed(feed)
    if live_only:
        return filter_matches(matches, live_only=True)
    return matches


def get_live_matches(sport: str = "tennis", locale: str = "es") -> list[dict]:
    """Partidos en juego ahora mismo."""
    return get_matches(sport=sport, locale=locale, live_only=True)


def get_finished_matches(
    sport: str = "tennis",
    day_offset: int = 0,
    locale: str = "es",
    *,
    enrich_scores: bool = True,
) -> list[dict]:
    """Partidos finalizados con marcador y ganador cuando está disponible."""
    client = FlashscoreClient(locale=locale)
    sport_id = client.sport_id(sport)
    feed = client.get_daily_feed(sport_id=sport_id, day_offset=day_offset)
    matches = dedupe_matches(parse_feed(feed))
    finished = [m for m in matches if is_finished_tennis_match(m)]

    if not enrich_scores or not finished:
        return build_finished_results(finished, {})

    pending = [m for m in finished if not has_decisive_score(m)]

    player_feeds: dict[str, dict[str, dict[str, str]]] = {}
    if pending:
        player_ids = {
            pid
            for match in pending
            for pid in (match.get("player1_id"), match.get("player2_id"))
            if pid
        }
        for player_id in player_ids:
            player_feeds[str(player_id)] = {}
            for page in range(4):
                try:
                    raw = client.get_player_results(str(player_id), sport_id=sport_id, page=page)
                    merge_player_feed_index(player_feeds[str(player_id)], raw)
                except FlashscoreError:
                    break

    extra_sources: dict[str, dict[str, str]] = {}
    for match in pending:
        match_id = match["id"]
        try:
            scoreboard = parse_scoreboard_feed(client.get_match_scoreboard(match_id))
            if scoreboard:
                extra_sources[match_id] = scoreboard
                continue
        except FlashscoreError:
            pass

        try:
            dc_raw = client.get_match_core(match_id)
            rows = _split_rows(dc_raw)
            if rows:
                dc_score = parse_dc_score(_parse_cells(rows[0]))
                if dc_score:
                    extra_sources[match_id] = dc_score
        except FlashscoreError:
            pass

    return build_finished_results(finished, player_feeds, extra_sources)


def get_match_statistics(match_id: str, locale: str = "es") -> dict:
    """Estadísticas detalladas de un partido por su ID."""
    client = FlashscoreClient(locale=locale)
    raw = client.get_match_stats(match_id)
    return parse_stats(raw)
