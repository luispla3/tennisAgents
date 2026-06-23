"""Búsqueda web con WebSearcher (https://github.com/gitronald/WebSearcher)."""

from __future__ import annotations

from typing import Any


def _result_value(result: Any, key: str) -> str:
    if isinstance(result, dict):
        value = result.get(key)
    else:
        value = getattr(result, key, None)
    return str(value) if value else ""


def _usable_results(results: list[Any]) -> list[Any]:
    usable = []
    for result in results:
        title = _result_value(result, "title")
        url = _result_value(result, "url")
        text = _result_value(result, "text")
        result_type = _result_value(result, "type").lower()
        if result_type in {"notice", "header"} and not (title or url or text):
            continue
        if title or url or text:
            usable.append(result)
    return usable


def _create_search_engine():
    from WebSearcher import SearchEngine

    try:
        from WebSearcher.models.configs import SearchMethod

        return SearchEngine(method=SearchMethod.REQUESTS)
    except ImportError:
        return SearchEngine(method="requests")


def perform_web_search(
    query: str,
    *,
    num_results: int = 10,
    lang: str = "es",
) -> str:
    """Ejecuta una búsqueda y devuelve un resumen legible de los resultados."""
    try:
        engine = _create_search_engine()
        engine.search(qry=query, num_results=num_results, lang=lang)
        engine.parse_serp()
        parsed_results = _usable_results(getattr(engine.parsed, "results", []) or [])
    except Exception as exc:
        return f"Error al buscar '{query}': {exc}"

    if not parsed_results:
        return f"No se encontraron resultados para: {query}"

    lines = [f"Resultados de búsqueda para: {query}\n"]
    for index, result in enumerate(parsed_results[:num_results], start=1):
        title = _result_value(result, "title") or "Sin título"
        url = _result_value(result, "url")
        snippet = _result_value(result, "text")
        lines.append(f"{index}. {title}")
        if url:
            lines.append(f"   URL: {url}")
        if snippet:
            lines.append(f"   {snippet}")
        lines.append("")

    return "\n".join(lines).strip()
