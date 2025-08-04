import os
import requests
from datetime import datetime
from typing import Dict, List, Optional

# Configuración de la API
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "ultimate-tennis1.p.rapidapi.com"


def get_tournament_list(year: Optional[int] = None, category: str = "atpgs") -> Dict:
    """
    Obtiene la lista de torneos del año especificado usando la Ultimate Tennis API.
    
    Args:
        year (int, optional): Año para consultar. Por defecto usa el año actual.
        category (str): Categoría de torneos. Opciones:
            - "atpgs": ATP tournaments + Grand Slams
            - "atp": ATP circuit
            - "gs": Grand Slams
            - "1000": Masters 1000
            - "ch": Challenger Circuit
    
    Returns:
        dict: Información de los torneos con sus IDs
    """
    if year is None:
        year = datetime.now().year
    
    if not RAPIDAPI_KEY:
        return {
            "error": "RAPIDAPI_KEY no configurada",
            "success": False
        }
    
    url = f"https://{RAPIDAPI_HOST}/tournament_list/atp/{year}/{category}"
    
    headers = {
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return {
                "error": f"API retornó status {response.status_code}",
                "message": response.text[:500] if response.text else "Sin mensaje de error",
                "year": year,
                "category": category,
                "success": False
            }
        
        data = response.json()
        
        # Extraer los IDs de los torneos
        tournament_ids = []
        if "Tournaments" in data:
            for tournament in data["Tournaments"]:
                if "ID" in tournament:
                    tournament_ids.append({
                        "id": tournament["ID"],
                        "name": tournament.get("Tournament Name", ""),
                        "location": tournament.get("Location", ""),
                        "timestamp": tournament.get("Timestamp", "")
                    })
        
        result = {
            "year": year,
            "category": category,
            "total_tournaments": len(tournament_ids),
            "tournament_ids": tournament_ids,
            "raw_data": data,
            "fetched_at": datetime.now().isoformat(),
            "success": True
        }

        print(f"[DEBUG] Resultado de get_tournament_list: {result}")
        
        return result
        
    except Exception as e:
        return {
            "error": f"Excepción ocurrida: {str(e)}",
            "year": year,
            "category": category,
            "success": False
        }


def fetch_tournament_info(tournament_name: str, year: int, category: str) -> str:
    """
    Obtiene el ID específico del torneo por nombre.
    
    Args:
        tournament_name (str): Nombre del torneo a buscar
        year (int, optional): Año para consultar. Por defecto usa el año actual.
        category (str): Categoría de torneos.
    
    Returns:
        str: ID del torneo si se encuentra, cadena vacía si no se encuentra
    """
    result = get_tournament_list(year, category)
    
    if not result.get("success", False):
        return ""
    
    # Buscar el torneo específico por nombre y extraer su ID
    tournament_id = ""
    if "tournament_ids" in result:
        for tournament in result["tournament_ids"]:
            if "name" in tournament and tournament["name"].lower() == tournament_name.lower():
                tournament_id = tournament["id"]
                break
    
    print(f"[DEBUG] ID del torneo: {tournament_id}")
    
    return tournament_id





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
