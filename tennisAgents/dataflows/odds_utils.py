import requests
import os
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