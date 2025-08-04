import requests
from datetime import datetime, timedelta
import json

def fetch_weather_forecast(latitude: float, longitude: float, fecha_hora: str, tournament: str) -> dict:
    """
    Obtiene el pronóstico meteorológico usando la API de Open-Meteo.
    
    Args:
        latitude (float): Latitud de la ubicación del torneo
        longitude (float): Longitud de la ubicación del torneo
        fecha_hora (str): Fecha y hora del partido en formato "yyyy-mm-dd hh:mm"
        tournament (str): Nombre del torneo 
    
    Returns:
        dict: Datos meteorológicos formateados
    """
    try:
        # Parsear la fecha y hora del partido
        match_datetime = datetime.strptime(fecha_hora, "%Y-%m-%d %H:%M")
        match_date = match_datetime.strftime("%Y-%m-%d")
        
        # Calcular fechas para el pronóstico (7 días desde la fecha del partido)
        start_date = match_date
        end_date = (match_datetime + timedelta(days=7)).strftime("%Y-%m-%d")
        
        # Construir la URL de la API de Open-Meteo
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,windspeed_10m,winddirection_10m,weathercode",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,weathercode",
            "timezone": "auto",
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return {
                "error": f"Error en la API: {response.status_code}",
                "success": False
            }
        
        data = response.json()
        
        if not data.get("daily") or not data["daily"]["time"]:
            return {
                "error": "No se encontraron datos meteorológicos",
                "success": False
            }
        
        # Mapeo de códigos de clima
        weather_code_map = {
            0: "Despejado",
            1: "Principalmente despejado",
            2: "Parcialmente nublado",
            3: "Nublado",
            45: "Niebla",
            48: "Niebla escarchada",
            51: "Llovizna ligera",
            53: "Llovizna moderada",
            55: "Llovizna intensa",
            56: "Llovizna helada ligera",
            57: "Llovizna helada intensa",
            61: "Lluvia ligera",
            63: "Lluvia moderada",
            65: "Lluvia intensa",
            66: "Lluvia helada ligera",
            67: "Lluvia helada intensa",
            71: "Nieve ligera",
            73: "Nieve moderada",
            75: "Nieve intensa",
            77: "Granizo",
            80: "Chubascos ligeros",
            81: "Chubascos moderados",
            82: "Chubascos intensos",
            85: "Chubascos de nieve ligeros",
            86: "Chubascos de nieve intensos",
            95: "Tormenta",
            96: "Tormenta con granizo ligero",
            99: "Tormenta con granizo intenso"
        }
        
        # Obtener datos del día del partido
        match_day_index = 0  # El primer día es el día del partido
        
        # Datos diarios
        daily_data = {
            "temp_max": data["daily"]["temperature_2m_max"][match_day_index],
            "temp_min": data["daily"]["temperature_2m_min"][match_day_index],
            "precip": data["daily"]["precipitation_sum"][match_day_index],
            "wind": data["daily"]["windspeed_10m_max"][match_day_index],
            "weather_code": data["daily"]["weathercode"][match_day_index],
            "description": weather_code_map.get(data["daily"]["weathercode"][match_day_index], "Desconocido")
        }
        
        # Obtener datos horarios para la hora específica del partido
        match_hour = match_datetime.hour
        hourly_data = None
        
        if "hourly" in data and data["hourly"]["time"]:
            # Buscar la hora más cercana al partido
            for i, time_str in enumerate(data["hourly"]["time"]):
                hourly_datetime = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                if hourly_datetime.hour == match_hour:
                    hourly_data = {
                        "temperature": data["hourly"]["temperature_2m"][i],
                        "humidity": data["hourly"]["relative_humidity_2m"][i],
                        "precipitation_prob": data["hourly"]["precipitation_probability"][i],
                        "precipitation": data["hourly"]["precipitation"][i],
                        "wind_speed": data["hourly"]["windspeed_10m"][i],
                        "wind_direction": data["hourly"]["winddirection_10m"][i],
                        "weather_code": data["hourly"]["weathercode"][i]
                    }
                    break
        
        # Preparar el resultado
        result = {
            "success": True,
            "tournament": tournament,
            "match_datetime": fecha_hora,
            "location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "daily_forecast": daily_data,
            "hourly_forecast": hourly_data,
            "weather_code_map": weather_code_map
        }
        
        return result
        
    except Exception as e:
        return {
            "error": f"Error al obtener datos meteorológicos: {str(e)}",
            "success": False
        }

def format_weather_report(weather_data: dict) -> str:
    """
    Formatea los datos meteorológicos en un reporte legible.
    
    Args:
        weather_data (dict): Datos meteorológicos de fetch_weather_forecast
    
    Returns:
        str: Reporte meteorológico formateado
    """
    if not weather_data.get("success", False):
        return f"❌ Error: {weather_data.get('error', 'Error desconocido')}"
    
    tournament = weather_data.get("tournament", "Torneo")
    match_datetime = weather_data.get("match_datetime", "")
    daily = weather_data.get("daily_forecast", {})
    hourly = weather_data.get("hourly_forecast", {})
    
    report = f"🌤️ **Pronóstico Meteorológico - {tournament}**\n\n"
    report += f"📅 **Fecha del partido:** {match_datetime}\n"
    report += f"📍 **Ubicación:** {weather_data['location']['latitude']:.4f}, {weather_data['location']['longitude']:.4f}\n\n"
    
    # Datos diarios
    report += "📊 **Pronóstico Diario:**\n"
    report += f"• Temperatura máxima: {daily.get('temp_max', 'N/A')}°C\n"
    report += f"• Temperatura mínima: {daily.get('temp_min', 'N/A')}°C\n"
    report += f"• Precipitación total: {daily.get('precip', 'N/A')} mm\n"
    report += f"• Velocidad del viento máxima: {daily.get('wind', 'N/A')} km/h\n"
    report += f"• Condiciones: {daily.get('description', 'N/A')}\n\n"
    
    # Datos horarios (si están disponibles)
    if hourly:
        report += "⏰ **Condiciones en la hora del partido:**\n"
        report += f"• Temperatura: {hourly.get('temperature', 'N/A')}°C\n"
        report += f"• Humedad: {hourly.get('humidity', 'N/A')}%\n"
        report += f"• Probabilidad de lluvia: {hourly.get('precipitation_prob', 'N/A')}%\n"
        report += f"• Precipitación: {hourly.get('precipitation', 'N/A')} mm\n"
        report += f"• Velocidad del viento: {hourly.get('wind_speed', 'N/A')} km/h\n"
        report += f"• Dirección del viento: {hourly.get('wind_direction', 'N/A')}°\n\n"
    
    # Análisis para tenis
    report += "🎾 **Análisis para Tenis:**\n"
    
    temp_max = daily.get('temp_max')
    temp_min = daily.get('temp_min')
    precip = daily.get('precip', 0)
    wind = daily.get('wind', 0)
    
    if temp_max is not None and temp_min is not None:
        temp_avg = (temp_max + temp_min) / 2
        
        if temp_avg < 10:
            report += "• ⚠️ Temperatura baja - puede afectar el rendimiento\n"
        elif temp_avg > 35:
            report += "• ⚠️ Temperatura alta - riesgo de agotamiento\n"
        else:
            report += "• ✅ Temperatura óptima para el tenis\n"
    
    if precip > 5:
        report += "• ⚠️ Precipitación significativa - posible retraso\n"
    elif precip > 0:
        report += "• ⚠️ Lluvia ligera - condiciones húmedas\n"
    else:
        report += "• ✅ Sin precipitación - condiciones ideales\n"
    
    if wind > 20:
        report += "• ⚠️ Viento fuerte - puede afectar el juego\n"
    elif wind > 10:
        report += "• ⚠️ Viento moderado - condiciones variables\n"
    else:
        report += "• ✅ Viento suave - condiciones estables\n"
    
    return report
