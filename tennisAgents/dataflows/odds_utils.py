import requests
import os
import random
from dotenv import load_dotenv
load_dotenv()  # Carga variables desde .env al entorno



def fetch_tennis_odds(player1: str, player2: str, match_date: str) -> dict:
    """
    Consulta cuotas de apuestas reales para un partido de tenis.
    """
    url = "https://api.the-odds-api.com/v4/sports/tennis/events"

    params = {
        "apiKey": THE_ODDS_API_KEY,
        "regions": "eu",           # Europa (o "us", "uk", etc.)
        "markets": "h2h",          # head-to-head
        "oddsFormat": "decimal",
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
    except Exception as e:
        print(f"[ERROR] Fallo al consultar Odds API: {e}")
        return {}

    for event in data:
        competitors = [c.lower() for c in event["teams"]]
        if player1.lower() in competitors and player2.lower() in competitors:
            odds_info = {}
            for bookmaker in event.get("bookmakers", []):
                try:
                    outcomes = bookmaker["markets"][0]["outcomes"]
                    odds_info[bookmaker["title"]] = {
                        "player1": outcomes[0]["price"],
                        "player2": outcomes[1]["price"],
                    }
                except:
                    continue
            return odds_info

    return {}


def generate_mock_odds(player1: str, player2: str) -> dict:
    """
    Genera cuotas aleatorias realistas entre 1.50 y 2.50 para pruebas de desarrollo.
    """
    cuota1 = round(random.uniform(1.50, 2.50), 2)
    cuota2 = round(random.uniform(1.50, 2.50), 2)

    return {
        "SimulatedBet365": {"player1": cuota1, "player2": cuota2},
        "SimulatedPinnacle": {
            "player1": round(cuota1 * random.uniform(0.95, 1.05), 2),
            "player2": round(cuota2 * random.uniform(0.95, 1.05), 2),
        },
    }
