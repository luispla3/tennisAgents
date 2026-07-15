from concurrent.futures import ThreadPoolExecutor, as_completed

from tennisAgents.dataflows.web_search_utils import perform_web_search, search_google_news

SEARCH_TIMEOUT_SECONDS = 30
NUM_RESULTS = 8


def fetch_news(query: str, curr_date: str) -> str:
    """Busca noticias recientes sobre un tema (Google News RSS + fallback web)."""
    header = f"## Noticias sobre '{query}' (búsqueda web, contexto {curr_date}):\n\n"
    for search_query in (
        f"{query} tennis ATP",
        f"{query} tennis",
    ):
        try:
            results = search_google_news(search_query, num_results=NUM_RESULTS, lang="en")
            if results and not results.startswith("No se encontraron"):
                return header + results
        except Exception:
            pass
        results = perform_web_search(search_query, num_results=NUM_RESULTS, lang="en")
        if results and not results.startswith("No se encontraron") and not results.startswith("Error"):
            return header + results
    return header + "Sin resultados en búsqueda web."


def fetch_news_for_match(player: str, opponent: str, tournament: str, curr_date: str) -> str:
    """Recopila noticias de ambos jugadores y del torneo en paralelo vía WebSearcher."""
    from tennisAgents.dataflows.tournament_utils import normalize_tournament

    tournament_query = normalize_tournament(tournament).search_name or tournament
    queries = [
        (player, player),
        (opponent, opponent),
        (tournament_query, tournament),
    ]

    parts: list[str] = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(fetch_news, query, curr_date): label
            for query, label in queries
        }
        for future in as_completed(futures):
            label = futures[future]
            try:
                parts.append(future.result(timeout=SEARCH_TIMEOUT_SECONDS))
            except Exception as exc:
                parts.append(f"## {label}\n\nNo se pudieron obtener noticias: {exc}")

    return "\n\n---\n\n".join(parts)
