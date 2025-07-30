import requests
from config import SPORTDEVS_API_KEY


def fetch_atp_rankings() -> list:
    """
    Recupera el ranking ATP desde SportDevs.
    """
    url = "https://api.sportdevs.com/tennis/players/rankings"
    headers = {
        "Authorization": f"Bearer {SPORTDEVS_API_KEY}"
    }
    params = {
        "gender": "men",  # ATP es masculino
        "type": "singles",  # individuales
        "limit": 10         # top 10
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"[ERROR] Fallo al obtener ranking ATP: {response.text}")
        return []

    data = response.json()
    rankings = []

    for player in data.get("data", []):
        rankings.append({
            "rank": player["rank"],
            "name": player["full_name"],
            "points": player["points"],
            "country": player["country"]["name"] if "country" in player else "N/D"
        })

    return rankings

def fetch_player_id(player_name: str) -> int:
    """
    Busca el ID de un jugador por su nombre completo.
    """
    url = "https://api.sportdevs.com/tennis/players"
    headers = {
        "Authorization": f"Bearer {SPORTDEVS_API_KEY}"
    }
    params = {
        "search": player_name
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"[ERROR] Fallo al buscar jugador: {response.text}")
        return None

    data = response.json()
    players = data.get("data", [])

    if not players:
        return None

    return players[0]["id"]

def fetch_recent_matches(player_name: str, num_matches: int = 5) -> list:
    """
    Recupera los últimos partidos jugados por un jugador.
    """
    player_id = fetch_player_id(player_name)
    if not player_id:
        return []

    url = f"https://api.sportdevs.com/tennis/players/{player_id}/matches"
    headers = {
        "Authorization": f"Bearer {SPORTDEVS_API_KEY}"
    }
    params = {
        "limit": num_matches,
        "order": "desc"  # partidos más recientes primero
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"[ERROR] Fallo al obtener partidos del jugador: {response.text}")
        return []

    data = response.json()
    matches = []

    for match in data.get("data", []):
        opponent = match["opponent"]["full_name"] if "opponent" in match else "N/D"
        matches.append({
            "date": match["start_date"][:10],
            "tournament": match["tournament"]["name"],
            "opponent": opponent,
            "result": match.get("score", "N/D"),
            "surface": match.get("surface", "N/D")
        })

    return matches


def fetch_surface_winrate(player_name: str, surface: str) -> dict:
    """
    Devuelve el winrate de un jugador en una superficie dada analizando sus partidos anteriores.
    """
    player_id = fetch_player_id(player_name)
    if not player_id:
        return None

    url = f"https://api.sportdevs.com/tennis/players/{player_id}/matches"
    headers = {
        "Authorization": f"Bearer {SPORTDEVS_API_KEY}"
    }
    params = {
        "limit": 50,
        "order": "desc"
    }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    if not data.get("data"):
        return None

    wins = 0
    losses = 0

    for match in data["data"]:
        match_surface = match.get("surface", "").lower()
        if match_surface != surface.lower():
            continue

        winner = match.get("winner", {}).get("full_name", "")
        if player_name.lower() in winner.lower():
            wins += 1
        else:
            losses += 1

    total = wins + losses
    if total == 0:
        return None

    return {
        "wins": wins,
        "losses": losses,
        "winrate": round((wins / total) * 100, 2)
    }

def fetch_head_to_head(player1: str, player2: str) -> dict:
    """
    Devuelve el historial de enfrentamientos (head-to-head) entre dos jugadores.
    """
    url = "https://api.sportdevs.com/tennis/matches/h2h"
    headers = {
        "Authorization": f"Bearer {SPORTDEVS_API_KEY}"
    }
    params = {
        "player1": player1,
        "player2": player2
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"[ERROR] Fallo en H2H: {response.text}")
        return None

    data = response.json()
    matches = data.get("data", [])

    if not matches:
        return None

    wins_p1 = 0
    wins_p2 = 0
    recent_matches = []

    for match in matches:
        winner = match.get("winner", {}).get("full_name", "")
        if player1.lower() in winner.lower():
            wins_p1 += 1
        elif player2.lower() in winner.lower():
            wins_p2 += 1

        recent_matches.append({
            "date": match["start_date"][:10],
            "tournament": match["tournament"]["name"],
            "winner": winner,
            "score": match.get("score", "N/A"),
            "surface": match.get("surface", "N/D")
        })

    recent_matches = sorted(recent_matches, key=lambda x: x["date"], reverse=True)[:5]

    return {
        "total": len(matches),
        "wins_p1": wins_p1,
        "wins_p2": wins_p2,
        "recent_matches": recent_matches
    }
