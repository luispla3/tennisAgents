"""Búsqueda web con WebSearcher, Google News RSS y fallback DuckDuckGo."""

from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlencode, urlparse
from typing import Any
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

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


def _parse_duckduckgo_html(html: str, num_results: int) -> list[dict[str, str]]:
    """Extrae resultados orgánicos desde la página HTML de DuckDuckGo."""
    soup = BeautifulSoup(html, "html.parser")
    parsed_results: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for result in soup.select(".result"):
        title_node = result.select_one(".result__a")
        if not title_node:
            continue

        title = title_node.get_text(" ", strip=True)
        url = title_node.get("href", "")
        if url.startswith("//duckduckgo.com/l/"):
            query_params = parse_qs(urlparse("https:" + url).query)
            if query_params.get("uddg"):
                url = unquote(query_params["uddg"][0])

        snippet_node = result.select_one(".result__snippet")
        snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""

        if not title and not snippet:
            continue
        if url and url in seen_urls:
            continue

        if url:
            seen_urls.add(url)
        parsed_results.append({"title": title, "url": url, "text": snippet})
        if len(parsed_results) >= num_results:
            break

    return parsed_results


def _duckduckgo_fallback(query: str, num_results: int, lang: str) -> list[dict[str, str]]:
    """Busca en DuckDuckGo HTML cuando WebSearcher no consigue parsear resultados."""
    attempts = [
        {"q": query, "kl": lang},
        {"q": query, "kl": "en"},
        {"q": query},
        {"q": query, "kl": "en-us"},
    ]

    last_response_text = ""
    for params in attempts:
        response = requests.get(
            "https://duckduckgo.com/html/",
            params=params,
            headers={"User-Agent": DEFAULT_USER_AGENT},
            timeout=15,
        )
        response.raise_for_status()
        last_response_text = response.text
        parsed_results = _parse_duckduckgo_html(response.text, num_results)
        if parsed_results:
            return parsed_results

    if not last_response_text:
        return []

    return _parse_duckduckgo_html(last_response_text, num_results)


def _google_news_rss_search(query: str, num_results: int, lang: str) -> list[dict[str, str]]:
    """Busca titulares recientes vía RSS de Google News."""
    hl = "en-US" if lang.startswith("en") else "es-ES"
    gl = "US" if lang.startswith("en") else "ES"
    ceid = "US:en" if lang.startswith("en") else "ES:es"
    url = "https://news.google.com/rss/search?" + urlencode(
        {"q": query, "hl": hl, "gl": gl, "ceid": ceid}
    )
    response = requests.get(
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT},
        timeout=20,
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)

    parsed_results: list[dict[str, str]] = []
    for item in root.findall(".//item")[:num_results]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        source = (item.findtext("source") or "").strip()
        meta = " | ".join(part for part in (pub_date, source) if part)
        if title or link:
            parsed_results.append({"title": title, "url": link, "text": meta})
    return parsed_results


def _format_search_results(query: str, parsed_results: list[Any], *, num_results: int) -> str:
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


def search_google_news(
    query: str,
    *,
    num_results: int = 10,
    lang: str = "en",
) -> str:
    """Busca titulares en Google News RSS."""
    parsed_results = _google_news_rss_search(query, num_results, lang)
    if not parsed_results:
        return f"No se encontraron resultados para: {query}"
    return _format_search_results(query, parsed_results, num_results=num_results)


def perform_web_search(
    query: str,
    *,
    num_results: int = 10,
    lang: str = "es",
) -> str:
    """Ejecuta una búsqueda y devuelve un resumen legible de los resultados."""
    search_error = None
    try:
        engine = _create_search_engine()
        engine.search(qry=query, num_results=num_results, lang=lang)
        engine.parse_serp()
        parsed_results = _usable_results(getattr(engine.parsed, "results", []) or [])
    except Exception as exc:
        search_error = exc
        parsed_results = []

    if not parsed_results:
        try:
            parsed_results = _duckduckgo_fallback(query, num_results, lang)
        except Exception as exc:
            search_error = search_error or exc
            parsed_results = []

    if not parsed_results:
        try:
            parsed_results = _google_news_rss_search(query, num_results, lang)
        except Exception as exc:
            if search_error:
                return (
                    f"Error al buscar '{query}' con WebSearcher: {search_error}. "
                    f"Fallback Google News falló: {exc}"
                )
            return f"Error al buscar '{query}': {exc}"

    if not parsed_results:
        return f"No se encontraron resultados para: {query}"

    return _format_search_results(query, parsed_results, num_results=num_results)
