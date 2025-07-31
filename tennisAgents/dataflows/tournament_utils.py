import os
import requests


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
