import requests

def fetch_weather_forecast(latitude: float, longitude: float, start_date: str, end_date: str) -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,weathercode",
        "timezone": "auto",
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return None

    data = response.json()
    if not data.get("daily") or not data["daily"]["time"]:
        return None

    day_index = 0  # solo buscamos 1 día
    weather_code_map = {
        0: "Despejado",
        1: "Principalmente despejado",
        2: "Parcialmente nublado",
        3: "Nublado",
        45: "Niebla",
        48: "Niebla escarchada",
        51: "Llovizna ligera",
        61: "Lluvia ligera",
        63: "Lluvia moderada",
        65: "Lluvia intensa",
        71: "Nieve ligera",
        80: "Chubascos ligeros",
        95: "Tormenta",
    }

    return {
        "temp_max": data["daily"]["temperature_2m_max"][day_index],
        "temp_min": data["daily"]["temperature_2m_min"][day_index],
        "precip": data["daily"]["precipitation_sum"][day_index],
        "wind": data["daily"]["windspeed_10m_max"][day_index],
        "description": weather_code_map.get(data["daily"]["weathercode"][day_index], "Desconocido"),
    }
