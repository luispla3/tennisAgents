from concurrent.futures import ThreadPoolExecutor, as_completed

from tennisAgents.dataflows.web_search_utils import perform_web_search

SEARCH_TIMEOUT_SECONDS = 30
NUM_RESULTS = 8


def fetch_news(query: str, curr_date: str) -> str:
    """Busca noticias recientes sobre un tema usando WebSearcher."""
    search_query = f"{query} tennis news {curr_date}"
    results = perform_web_search(search_query, num_results=NUM_RESULTS, lang="en")

    header = f"## Noticias sobre '{query}' (búsqueda web, {curr_date}):\n\n"
    if results:
        return header + results
    return header + "Sin resultados en búsqueda web."


def fetch_news_for_match(player: str, opponent: str, tournament: str, curr_date: str) -> str:
    """Recopila noticias de ambos jugadores y del torneo en paralelo vía WebSearcher."""
    queries = [
        (player, player),
        (opponent, opponent),
        (tournament, tournament),
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
