import os
import requests

# Diccionario de superficies conocidas por torneo
TOURNAMENT_SURFACES = {
    "australian_open": "hard",
    "french_open": "clay", 
    "wimbledon": "grass",
    "us_open": "hard",
    
    "indian_wells": "hard",
    "miami_open": "hard",
    "monte_carlo": "clay",
    "madrid_open": "clay",
    "italian_open": "clay",
    "canadian_open": "hard",
    "cincinnati_open": "hard",
    "shanghai_masters": "hard",
    "paris_masters": "hard",
    
    "dubai": "hard",
    "qatar_open": "hard",
    "china_open": "hard",

    "wta_australian_open": "hard",
    "wta_french_open": "clay",
    "wta_wimbledon": "grass",
    "wta_us_open": "hard",
    "wta_indian_wells": "hard",
    "wta_miami_open": "hard",
    "wta_madrid_open": "clay",
    "wta_italian_open": "clay",
    "wta_canadian_open": "hard",
    "wta_cincinnati_open": "hard",
    "wta_dubai": "hard",
    "wta_qatar_open": "hard",
    "wta_china_open": "hard",
    "wta_wuhan_open": "hard",
}

def get_tournament_surface(tournament_key: str) -> str:
    """
    Obtiene la superficie de un torneo basándose en el nombre del torneo.
    
    Args:
        tournament_key (str): Key del torneo
        
    Returns:
        str: Superficie del torneo ('hard', 'clay', 'grass') o 'hard' como fallback
    """
    # Normalizar el nombre del torneo
    tournament_normalized = tournament_key.lower().strip()
    
    # Buscar coincidencia exacta
    if tournament_normalized in TOURNAMENT_SURFACES:
        return TOURNAMENT_SURFACES[tournament_normalized]
    
    # Buscar coincidencias parciales
    for key, surface in TOURNAMENT_SURFACES.items():
        if key in tournament_normalized or tournament_normalized in key:
            return surface
    
    # Fallback basado en palabras clave
    if any(keyword in tournament_normalized for keyword in ["clay", "terre", "arcilla"]):
        return "clay"
    elif any(keyword in tournament_normalized for keyword in ["grass", "hierba", "césped"]):
        return "grass"
    elif any(keyword in tournament_normalized for keyword in ["hard", "dura", "cemento"]):
        return "hard"
    
    # Fallback por defecto (la mayoría de torneos son hard court)
    return "hard"


def fetch_tournament_info(tournament: str, year: int) -> dict:
    url = f"{BASE_URL_SPORTDEVS}/tournaments"
    params = {
        "year": year,
        "name": tournament,
        "apiKey": SPORTDEVS_KEY
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"[ERROR] Fallo al obtener torneo: {response.text}")
        return None

    data = response.json()
    if not data.get("data"):
        return None

    torneo = data["data"][0]

    return {
        "name": torneo["name"],
        "location": torneo.get("location", "Desconocida"),
        "surface": torneo.get("surface", "Desconocida"),
        "start_date": torneo.get("start_date", "N/D"),
        "end_date": torneo.get("end_date", "N/D"),
        "winner": torneo.get("winner", "N/D"),
        "runner_up": torneo.get("runner_up", "N/D"),
        "notables": torneo.get("notable_players", [])[:5],
    }

def get_mock_data(tournament: str, year: int) -> dict:
    return {
        "name": tournament,
        "location": "Ciudad Simulada",
        "surface": "hard",
        "start_date": f"{year}-03-15",
        "end_date": f"{year}-03-21",
        "winner": "Jugador Simulado A",
        "runner_up": "Jugador Simulado B",
        "notables": ["Jugador Simulado C", "Jugador Simulado D", "Jugador Simulado E"],
    }
