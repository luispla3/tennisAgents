from tennisAgents.dataflows.config import get_config
from tennisAgents.dataflows.llm_utils import invoke_chat_llm, invoke_local_analyst_llm
from tennisAgents.dataflows.web_search_utils import perform_web_search


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

        if config.get("use_local_analysts", False):
            try:
                local_model = config.get("local_model_name", "qwen2.5:3b")
                text, label = invoke_local_analyst_llm(
                    "Eres un experto meteorólogo deportivo.",
                    (
                        f"Genera un pronóstico del tiempo SIMULADO y plausible para {location} "
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
                    "location": location,
                    "weather_info": weather_info,
                    "source": source_name,
                    "timestamp": "2025-01-01 00:00:00",
                }
            except Exception as e:
                return {
                    "error": f"Error usando modelo para clima: {str(e)}",
                    "tournament": tournament,
                    "fecha_hora": fecha_hora,
                    "location": location,
                }

        search_query = f"weather forecast {location} {fecha_hora} {tournament}"
        search_context = perform_web_search(search_query)

        system_prompt = f"""
        Busca información meteorológica detallada para la ubicación {location}
        para la fecha {fecha_hora} donde se jugará el torneo {tournament}.

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
            "location": location,
            "weather_info": weather_info,
            "source": "WebSearcher",
            "timestamp": "2025-01-01 00:00:00",
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

        report = f"""
# PRONÓSTICO METEOROLÓGICO - {tournament.upper()}

**Fecha del partido:** {fecha_hora}
**Ubicación:** {location}

## CONDICIONES CLIMÁTICAS ESPERADAS

{weather_info}

---
*Información obtenida mediante: {source}*
        """

        return report.strip()

    except Exception as e:
        return f"Error al formatear el reporte meteorológico: {str(e)}"

