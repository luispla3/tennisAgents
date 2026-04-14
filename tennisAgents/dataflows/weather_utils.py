import os
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from tennisAgents.dataflows.config import get_config

def fetch_weather_forecast(location: str, fecha_hora: str, tournament: str) -> dict:
    """
    Obtiene el pronóstico meteorológico usando OpenAI con búsqueda web o modelo local simulado.
    
    Args:
        location (str): Ubicación del torneo (ciudad, país, etc.)
        fecha_hora (str): Fecha y hora del partido en formato "yyyy-mm-dd hh:mm"
        tournament (str): Nombre del torneo 
    
    Returns:
        dict: Datos meteorológicos formateados
    """
    try:
        config = get_config()
        
        # Check if we should use local (Ollama) or OpenRouter analyst model
        if config.get("use_local_analysts", False):
            try:
                local_base_url = config.get("local_base_url", "http://localhost:11434/v1")
                local_model = config.get("local_model_name", "qwen2.5:3b")
                is_local = "localhost" in local_base_url or "127.0.0.1" in local_base_url
                
                if is_local:
                    # Ollama local
                    base_url_cleaned = local_base_url.replace("/v1", "") if local_base_url.endswith("/v1") else local_base_url
                    llm = ChatOllama(
                        model=local_model,
                        base_url=base_url_cleaned,
                        temperature=0.1,
                    num_ctx=16384,
                    num_predict=4096,
                    reasoning=False
                )
                    source_label = "OLLAMA LOCAL"
                    source_name = f"Ollama {local_model}"
                else:
                    # OpenRouter
                    local_api_key = config.get("local_api_key") or os.getenv("OPENROUTER_API_KEY")
                    if not local_api_key:
                        raise ValueError("OPENROUTER_API_KEY no configurada")
                    llm = ChatOpenAI(
                        model=local_model,
                        base_url=local_base_url,
                        api_key=local_api_key,
                        default_headers={
                            "HTTP-Referer": "https://github.com/tennisAgents",
                            "X-Title": "Tennis Agents"
                        },
                        temperature=0.7
                    )
                    source_label = "OPENROUTER"
                    source_name = f"OpenRouter {local_model}"
                    
                messages = [
                    SystemMessage(content="Eres un experto meteorólogo deportivo."),
                    HumanMessage(content=f"Genera un pronóstico del tiempo SIMULADO y plausible para {location} en la fecha {fecha_hora} durante el torneo {tournament}. Incluye temperatura, viento, humedad y probabilidad de lluvia basándote en el clima típico de esa región en esa época del año. Aclara que esto es una estimación basada en patrones históricos y no un pronóstico real.")
                ]
                
                response = llm.invoke(messages)
                weather_info = f"[ANÁLISIS VIA {source_label} - BASADO EN PATRONES HISTÓRICOS]\n{response.content}"
                
                return {
                    "tournament": tournament,
                    "fecha_hora": fecha_hora,
                    "location": location,
                    "weather_info": weather_info,
                    "source": source_name,
                    "timestamp": "2025-01-01 00:00:00"
                }
            except Exception as e:
                return {
                    "error": f"Error usando modelo para clima: {str(e)}",
                    "tournament": tournament,
                    "fecha_hora": fecha_hora,
                    "location": location
                }

        # Original implementation with OpenAI Web Search
        client = OpenAI(base_url=config["backend_url"])

        # Crear el prompt para OpenAI
        prompt_text = f"""
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
            "location": location,
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
            "location": location
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
        source = weather_data.get("source", "OpenAI Web Search")
        
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