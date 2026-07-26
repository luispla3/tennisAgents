from tennisAgents.dataflows.config import get_config
from tennisAgents.dataflows.llm_utils import invoke_chat_llm, invoke_local_analyst_llm
from tennisAgents.dataflows.tournament_utils import normalize_tournament, resolve_weather_location
from tennisAgents.dataflows.web_search_utils import perform_web_search

import requests


def _open_meteo_forecast(location: str, fecha_hora: str, tournament: str) -> dict | None:
    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": location, "count": 1, "language": "en", "format": "json"},
        timeout=10,
    )
    geo.raise_for_status()
    results = geo.json().get("results") or []
    if not results:
        return None

    place = results[0]
    forecast = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "daily": (
                "temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max,wind_speed_10m_max"
            ),
            "timezone": place.get("timezone", "auto"),
        },
        timeout=10,
    )
    forecast.raise_for_status()
    data = forecast.json()
    match_date = str(fecha_hora).split()[0]
    daily = data.get("daily") or {}
    dates = daily.get("time") or []
    if match_date not in dates:
        return None

    idx = dates.index(match_date)
    weather_info = (
        f"Datos Open-Meteo para {place.get('name')}, {place.get('country')} "
        f"({match_date}):\n"
        f"- Temperatura máxima: {daily.get('temperature_2m_max', [None])[idx]} °C\n"
        f"- Temperatura mínima: {daily.get('temperature_2m_min', [None])[idx]} °C\n"
        f"- Probabilidad máxima de precipitación: "
        f"{daily.get('precipitation_probability_max', [None])[idx]}%\n"
        f"- Viento máximo a 10m: {daily.get('wind_speed_10m_max', [None])[idx]} km/h\n"
        f"- Elevación aproximada: {place.get('elevation', 'N/D')} m\n"
    )
    return {
        "tournament": tournament,
        "fecha_hora": fecha_hora,
        "location": f"{place.get('name')}, {place.get('country')}",
        "weather_info": weather_info,
        "source": "Open-Meteo",
        "timestamp": data.get("generationtime_ms", ""),
    }


def _weather_location_candidates(location: str, tournament: str) -> tuple[list[str], dict[str, str | bool | None]]:
    identity = normalize_tournament(tournament or location)
    resolved_location, location_verified, location_note = resolve_weather_location(
        tournament or location,
        location,
    )
    candidates = [
        resolved_location,
        identity.location,
        location,
        identity.search_name,
        tournament,
    ]
    deduped: list[str] = []
    for candidate in candidates:
        cleaned = " ".join(str(candidate or "").split())
        if cleaned and cleaned not in deduped:
            deduped.append(cleaned)

    metadata = {
        "resolved_location": resolved_location,
        "official_location": identity.location if identity.official_name else None,
        "official_tournament": identity.official_name,
        "calendar_source": identity.calendar_source,
        "location_verified": location_verified,
        "location_note": location_note,
    }
    return deduped, metadata


def fetch_weather_forecast(location: str, fecha_hora: str, tournament: str) -> dict:
    """
    Obtiene el pronóstico meteorológico usando búsqueda web + LLM o modelo local simulado.

    Args:
        location (str): Ubicación del torneo (ciudad, país, etc.)
        fecha_hora (str): Fecha y hora del partido en formato "yyyy-mm-dd hh:mm"
        tournament (str): Nombre del torneo

    Returns:
        dict: Datos meteorológicos formateados
    """
    try:
        config = get_config()
        candidates, location_metadata = _weather_location_candidates(location, tournament)

        for candidate in candidates:
            try:
                open_meteo = _open_meteo_forecast(candidate, fecha_hora, tournament)
                if open_meteo:
                    open_meteo.update(location_metadata)
                    open_meteo["location"] = location_metadata.get("resolved_location") or open_meteo.get("location")
                    return open_meteo
            except Exception:
                continue

        identity = normalize_tournament(tournament or location)
        fallback_location = (
            location_metadata.get("resolved_location")
            or identity.location
            or identity.search_name
            or location
        )

        if config.get("use_local_analysts", False):
            try:
                local_model = config.get("local_model_name", "qwen2.5:3b")
                text, label = invoke_local_analyst_llm(
                    "Eres un experto meteorólogo deportivo.",
                    (
                        f"Genera un pronóstico del tiempo SIMULADO y plausible para {fallback_location} "
                        f"en la fecha {fecha_hora} durante el torneo {tournament}. Incluye temperatura, "
                        f"viento, humedad y probabilidad de lluvia basándote en el clima típico de esa "
                        f"región en esa época del año. Aclara que esto es una estimación basada en "
                        f"patrones históricos y no un pronóstico real."
                    ),
                )
                source_name = f"Ollama {local_model}" if label == "OLLAMA LOCAL" else f"OpenRouter {local_model}"
                weather_info = f"[ANÁLISIS VIA {label} - BASADO EN PATRONES HISTÓRICOS]\n{text}"
                return {
                    "tournament": tournament,
                    "fecha_hora": fecha_hora,
                    "location": fallback_location,
                    "weather_info": weather_info,
                    "source": source_name,
                    "timestamp": "2025-01-01 00:00:00",
                    **location_metadata,
                }
            except Exception as e:
                return {
                    "error": f"Error usando modelo para clima: {str(e)}",
                    "tournament": tournament,
                    "fecha_hora": fecha_hora,
                    "location": location,
                }

        search_query = f"{fallback_location} weather forecast {fecha_hora.split()[0]}"
        search_context = perform_web_search(search_query)

        system_prompt = f"""
        Resume la información meteorológica disponible para {fallback_location}
        alrededor del {fecha_hora}. Torneo: {identity.display_name}.
        """
        if identity.official_name and identity.location:
            system_prompt += (
                f"\nUbicación oficial del calendario ATP 2026: {identity.location}."
            )
            if location_metadata.get("location_note"):
                system_prompt += f"\n{location_metadata['location_note']}"

        system_prompt += """

        Necesito información específica sobre:
        - Temperatura máxima y mínima (en Celsius)
        - Velocidad del viento (en km/h)
        - Dirección del viento
        - Humedad relativa (%)
        - Probabilidad de precipitación (%)
        - Cantidad de precipitación esperada (mm)
        - Presión atmosférica (hPa)
        - Condiciones generales del cielo (despejado, nublado, lluvia, etc.)

        Devuelve un análisis detallado y específico con datos cuantitativos precisos.
        """

        weather_info = invoke_chat_llm(
            system_prompt,
            f"Resultados de búsqueda web:\n\n{search_context}",
        )

        return {
            "tournament": tournament,
            "fecha_hora": fecha_hora,
            "location": fallback_location,
            "weather_info": weather_info,
            "source": "WebSearcher",
            "timestamp": "2025-01-01 00:00:00",
            **location_metadata,
        }

    except Exception as e:
        return {
            "error": f"Error al obtener pronóstico meteorológico: {str(e)}",
            "tournament": tournament,
            "fecha_hora": fecha_hora,
            "location": location,
        }


def format_weather_report(weather_data: dict) -> str:
    """
    Formatea los datos meteorológicos en un reporte legible.

    Args:
        weather_data (dict): Datos meteorológicos obtenidos

    Returns:
        str: Reporte meteorológico formateado
    """
    if "error" in weather_data:
        return f"Error en el pronóstico meteorológico: {weather_data['error']}"

    try:
        tournament = weather_data.get("tournament", "Torneo desconocido")
        fecha_hora = weather_data.get("fecha_hora", "Fecha desconocida")
        location = weather_data.get("location", "Ubicación desconocida")
        weather_info = weather_data.get("weather_info", "Información meteorológica no disponible")
        source = weather_data.get("source", "LLM + Web Search")
        official_tournament = weather_data.get("official_tournament")
        official_location = weather_data.get("official_location")
        location_verified = weather_data.get("location_verified")
        location_note = weather_data.get("location_note")

        verification_lines = []
        if official_tournament:
            verification_lines.append(f"**Torneo oficial:** {official_tournament}")
        if official_location:
            verified_label = "sí" if location_verified else "no"
            verification_lines.append(
                f"**Ubicación oficial (calendario 2026):** {official_location} "
                f"(coincide con la recibida: {verified_label})"
            )
        if location_note:
            verification_lines.append(f"**Nota de ubicación:** {location_note}")

        verification_block = ""
        if verification_lines:
            verification_block = "## VERIFICACIÓN DE UBICACIÓN\n\n" + "\n".join(verification_lines) + "\n\n"

        report = f"""
# PRONÓSTICO METEOROLÓGICO - {tournament.upper()}

**Fecha del partido:** {fecha_hora}
**Ubicación:** {location}

{verification_block}## CONDICIONES CLIMÁTICAS ESPERADAS

{weather_info}

---
*Información obtenida mediante: {source}*
        """

        return report.strip()

    except Exception as e:
        return f"Error al formatear el reporte meteorológico: {str(e)}"

