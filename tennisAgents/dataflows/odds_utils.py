import requests
import os
import random
from datetime import datetime

def fetch_tennis_odds(tournament_key: str) -> dict:
    """
    Consulta cuotas de apuestas para un torneo específico usando The Odds API.
    
    Args:
        tournament_key (str): Clave del torneo según The Odds API (ej: "tennis_atp_canadian_open").
    
    Returns:
        dict: Todos los eventos y cuotas del torneo consultado.
    """
    url = f"https://api.the-odds-api.com/v4/sports/{tournament_key}/odds"

    THE_ODDS_API_KEY = os.environ.get("THE_ODDS_API_KEY")
    if not THE_ODDS_API_KEY:
        return {"error": "API key not configured"}

    params = {
        "apiKey": THE_ODDS_API_KEY,
        "regions": "eu,us,uk",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal",
    }

    try:
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            return {
                "error": f"API returned status {response.status_code}",
                "message": response.text[:500] if response.text else "No error message",
                "tournament": tournament_key
            }
        
        data = response.json()


        result = {
            "tournament": tournament_key,
            "total_events": len(data),
            "events": data,
            "fetched_at": datetime.now().isoformat(),
            "success": True
        }
        
        return result
        
    except Exception as e:
        return {
            "error": f"Exception occurred: {str(e)}",
            "tournament": tournament_key,
            "success": False
        }

def generate_mock_odds(player1: str, player2: str) -> dict:
    """
    Genera cuotas aleatorias realistas entre 1.50 y 2.50 para pruebas de desarrollo.
    
    Args:
        player1 (str): Nombre del primer jugador.
        player2 (str): Nombre del segundo jugador.
    
    Returns:
        dict: Cuotas simuladas con estructura similar a la API real.
    """
    prob1 = random.uniform(0.4, 0.6)  
    cuota1 = round(1 / prob1, 2)
    cuota2 = round(1 / (1 - prob1), 2)
    
    mock_data = {
        "match_info": {
            "home_team": player1,
            "away_team": player2,
            "commence_time": datetime.now().isoformat() + "Z",
            "sport_title": "Mock Tennis Tournament",
            "tournament": "mock_tournament"
        },
        "bookmakers": {
            "bet365": {
                "title": "Bet365",
                "h2h": {"player1": cuota1, "player2": cuota2}
            },
            "pinnacle": {
                "title": "Pinnacle",
                "h2h": {
                    "player1": round(cuota1 * random.uniform(0.95, 1.05), 2),
                    "player2": round(cuota2 * random.uniform(0.95, 1.05), 2)
                }
            }
        }
    }
    
    return mock_data