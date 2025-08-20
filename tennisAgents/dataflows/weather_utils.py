from openai import OpenAI
from tennisAgents.dataflows.config import get_config

def fetch_weather_forecast(latitude: float, longitude: float, fecha_hora: str, tournament: str) -> dict:
    """
    Obtiene el pronóstico meteorológico usando OpenAI con búsqueda web.
    
    Args:
        latitude (float): Latitud de la ubicación del torneo
        longitude (float): Longitud de la ubicación del torneo
        fecha_hora (str): Fecha y hora del partido en formato "yyyy-mm-dd hh:mm"
        tournament (str): Nombre del torneo 
    
    Returns:
        dict: Datos meteorológicos formateados
    """
    try:
        config = get_config()
        client = OpenAI(base_url=config["backend_url"])

        # Crear el prompt para OpenAI
        prompt_text = f"""
        Busca información meteorológica detallada para la ubicación con coordenadas {latitude}, {longitude} 
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

        response = client.responses.create(
            model=config["quick_think_llm"],
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt_text,
                        }
                    ],
                }
            ],
            text={"format": {"type": "text"}},
            reasoning={},
            tools=[
                {
                    "type": "web_search_preview",
                    "user_location": {"type": "approximate"},
                    "search_context_size": "medium",
                }
            ],
            temperature=1,
            max_output_tokens=4096,
            top_p=1,
            store=True,
        )

        weather_info = response.output[1].content[0].text

        # Crear un diccionario estructurado con la información obtenida
        weather_data = {
            "tournament": tournament,
            "fecha_hora": fecha_hora,
            "latitude": latitude,
            "longitude": longitude,
            "weather_info": weather_info,
            "source": "OpenAI Web Search",
            "timestamp": "2025-01-01 00:00:00"  # Placeholder timestamp
        }

        return weather_data

    except Exception as e:
        return {
            "error": f"Error al obtener pronóstico meteorológico: {str(e)}",
            "tournament": tournament,
            "fecha_hora": fecha_hora,
            "latitude": latitude,
            "longitude": longitude
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
        weather_info = weather_data.get("weather_info", "Información meteorológica no disponible")
        
        report = f"""
# PRONÓSTICO METEOROLÓGICO - {tournament.upper()}

**Fecha del partido:** {fecha_hora}
**Ubicación:** Coordenadas {weather_data.get('latitude', 'N/A')}, {weather_data.get('longitude', 'N/A')}

## CONDICIONES CLIMÁTICAS ESPERADAS

{weather_info}

---
*Información obtenida mediante análisis de OpenAI con búsqueda web*
        """
        
        return report.strip()
        
    except Exception as e:
        return f"Error al formatear el reporte meteorológico: {str(e)}"
