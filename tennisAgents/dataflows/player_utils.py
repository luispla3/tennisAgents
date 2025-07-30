import requests
import os
from dotenv import load_dotenv
load_dotenv()  # Carga variables desde .env al entorno



def fetch_atp_rankings() -> list:
    """
    Recupera el ranking ATP desde API-Sports Tennis.
    """
    url = "https://v1.tennis.api-sports.io/rankings/atp"
    headers = {
        "x-rapidapi-key": API_SPORTS_TENNIS_KEY,
        "x-rapidapi-host": "v1.tennis.api-sports.io",
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"[ERROR] Fallo al obtener ranking ATP: {response.text}")
        return []

    data = response.json()
    rankings = []

    for player in data["response"][0]["players"][:10]:  # Top 10
        rankings.append({
            "rank": player["ranking"],
            "name": player["name"],
            "points": player["points"],
            "country": player["country"]["name"]
        })

    return rankings


HEADERS = {
    "x-rapidapi-key": API_SPORTS_TENNIS_KEY,
    "x-rapidapi-host": "v1.tennis.api-sports.io",
}

def fetch_player_id(player_name: str) -> int:
    url = f"{BASE_URL_SPORTS_TENNIS}/players"
    params = {"search": player_name}
    r = requests.get(url, headers=HEADERS, params=params)
    data = r.json()

    if not data["response"]:
        return None

    return data["response"][0]["id"]

def fetch_recent_matches(player_name: str, num_matches: int = 5) -> list:
    player_id = fetch_player_id(player_name)
    if not player_id:
        return []

    url = f"{BASE_URL_SPORTS_TENNIS}/players/results"
    params = {
        "id": player_id,
        "limit": num_matches
    }

    r = requests.get(url, headers=HEADERS, params=params)
    data = r.json()

    if not data.get("response"):
        return []

    matches = []
    for match in data["response"]:
        matches.append({
            "date": match["date"][:10],
            "tournament": match["tournament"]["name"],
            "opponent": match["opponent"]["name"],
            "result": match["score"],
            "surface": match.get("surface", "N/D")
        })

    return matches

import requests
import os



def fetch_player_id(player_name: str) -> int:
    url = f"{BASE_URL_SPORTS_TENNIS}/players"
    params = {"search": player_name}
    r = requests.get(url, headers=HEADERS, params=params)
    data = r.json()

    if not data["response"]:
        return None

    return data["response"][0]["id"]

def fetch_surface_winrate(player_name: str, surface: str) -> dict:
    """
    Devuelve el winrate de un jugador en una superficie dada usando sus partidos anteriores.
    """
    player_id = fetch_player_id(player_name)
    if not player_id:
        return None

    url = f"{BASE_URL_SPORTS_TENNIS}/players/results"
    params = {"id": player_id, "limit": 50}  # analizando últimos 50 partidos

    r = requests.get(url, headers=HEADERS, params=params)
    data = r.json()
    if not data.get("response"):
        return None

    wins = 0
    losses = 0

    for match in data["response"]:
        match_surface = match.get("surface", "").lower()
        if match_surface != surface.lower():
            continue

        # Determinar si ganó o perdió
        winner = match["winner"]["name"]
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
    Consulta el historial de enfrentamientos entre dos jugadores usando la API de API-Sports Tennis.
    """
    url = f"{BASE_URL_SPORTS_TENNIS}/players/headtohead"
    params = {"player1": player1, "player2": player2}

    r = requests.get(url, headers=HEADERS, params=params)
    data = r.json()

    if not data.get("response"):
        return None

    matches = data["response"]
    wins_p1 = 0
    wins_p2 = 0
    recent_matches = []

    for match in matches:
        winner = match["winner"]["name"]
        if player1.lower() in winner.lower():
            wins_p1 += 1
        elif player2.lower() in winner.lower():
            wins_p2 += 1

        recent_matches.append({
            "date": match["date"][:10],
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
