import requests
import os
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Usar la nueva API de tenis ATP/WTA/ITF de RapidAPI
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = "tennis-api-atp-wta-itf.p.rapidapi.com"


def fetch_atp_rankings() -> list:
    """
    Recupera el ranking ATP desde la API de tenis ATP/WTA/ITF.
    """
    if not RAPIDAPI_KEY:
        print("[ERROR] RAPIDAPI_KEY no está configurada")
        return []
    
    # URL correcta para rankings ATP según RapidAPI
    url = f"https://{RAPIDAPI_HOST}/tennis/v2/atp/ranking/singles/"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    # No necesitamos parámetros para este endpoint
    params = {}

    try:
        print(f"[DEBUG] Intentando obtener ranking ATP desde RapidAPI...")
        print(f"[DEBUG] URL: {url}")
        response = requests.get(url, headers=headers, params=params, timeout=10)

        print(f"[DEBUG] Status code: {response.status_code}")
        
        if response.status_code == 401:
            print("[ERROR] API key inválida o no autorizada")
            return []
        elif response.status_code == 403:
            print("[ERROR] Acceso denegado - verifica tu plan de suscripción")
            return []
        elif response.status_code != 200:
            print(f"[ERROR] Fallo al obtener ranking ATP: {response.status_code}")
            print(f"[DEBUG] Response: {response.text}")
            return []

        data = response.json()
        print(f"[DEBUG] Datos recibidos de RapidAPI")
        print(f"[DEBUG] Response keys: {list(data.keys()) if isinstance(data, dict) else 'No es dict'}")
        
        rankings = []

        # Según la imagen de RapidAPI, los datos están en data["data"]
        players_data = data.get("data", [])
        
        print(f"[DEBUG] Jugadores encontrados: {len(players_data)}")
        
        for i, player_data in enumerate(players_data[:10]):  # Top 10
            print(f"[DEBUG] Procesando jugador {i+1}: {player_data}")
            
            # Extraer datos según la estructura correcta
            player_info = player_data.get("player", {})
            
            rank = player_data.get("position", "N/D")
            name = player_info.get("name", "N/D")
            points = player_data.get("point", "N/D")
            country = player_info.get("country", {}).get("name", player_info.get("countryAcr", "N/D"))
            
            rankings.append({
                "rank": rank,
                "name": name,
                "points": points,
                "country": country
            })
            
            print(f"[DEBUG] Jugador procesado: {rank}. {name} ({country}) - {points} pts")

        print(f"[INFO] Ranking ATP obtenido exitosamente: {len(rankings)} jugadores")
        return rankings
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de conexión al obtener ranking ATP: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Error inesperado al obtener ranking ATP: {e}")
        return []

def fetch_player_id(player_name: str) -> int:
    """
    Busca el ID de un jugador por su nombre completo usando la API de tenis.
    """
    if not RAPIDAPI_KEY:
        print("[ERROR] RAPIDAPI_KEY no está configurada")
        return None
    
    # Endpoint de búsqueda de jugadores
    url = f"https://{RAPIDAPI_HOST}/tennis/v2/search"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    params = {
        "search": player_name
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code != 200:
            print(f"[ERROR] Fallo al buscar jugador: {response.status_code} - {response.text}")
            return None

        data = response.json()
        players = data.get("players", [])
        if not players:
            players = data.get("data", [])

        if not players:
            print(f"[INFO] No se encontró el jugador: {player_name}")
            return None

        return players[0]["id"]
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de conexión al buscar jugador: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Error inesperado al buscar jugador: {e}")
        return None

def fetch_recent_matches(player_name: str, num_matches: int = 5) -> list:
    """
    Recupera los últimos partidos jugados por un jugador usando la API de tenis.
    """
    if not RAPIDAPI_KEY:
        print("[ERROR] RAPIDAPI_KEY no está configurada")
        return []
    
    player_id = fetch_player_id(player_name)
    if not player_id:
        return []

    url = f"https://{RAPIDAPI_HOST}/tennis/v2/players/{player_id}/matches"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    params = {
        "limit": num_matches
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code != 200:
            print(f"[ERROR] Fallo al obtener partidos del jugador: {response.status_code} - {response.text}")
            return []

        data = response.json()
        matches = []

        for match in data.get("matches", []):
            matches.append({
                "date": match.get("date", "N/D")[:10],
                "tournament": match.get("tournament", {}).get("name", "N/D"),
                "opponent": match.get("opponent", {}).get("name", "N/D"),
                "result": match.get("score", "N/D"),
                "surface": match.get("surface", "N/D")
            })

        return matches
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de conexión al obtener partidos: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Error inesperado al obtener partidos: {e}")
        return []


def fetch_surface_winrate(player_name: str, surface: str) -> dict:
    """
    Devuelve el winrate de un jugador en una superficie dada usando la API de tenis.
    """
    if not RAPIDAPI_KEY:
        print("[ERROR] RAPIDAPI_KEY no está configurada")
        return None
    
    player_id = fetch_player_id(player_name)
    if not player_id:
        return None

    url = f"https://{RAPIDAPI_HOST}/tennis/v2/players/{player_id}/matches"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    params = {
        "limit": 50
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code != 200:
            print(f"[ERROR] Fallo al obtener partidos para winrate: {response.status_code} - {response.text}")
            return None

        data = response.json()
        if not data.get("matches"):
            print(f"[INFO] No se encontraron partidos para {player_name}")
            return None

        wins = 0
        losses = 0

        for match in data["matches"]:
            match_surface = match.get("surface", "").lower()
            if match_surface != surface.lower():
                continue

            winner = match.get("winner", {}).get("name", "")
            if player_name.lower() in winner.lower():
                wins += 1
            else:
                losses += 1

        total = wins + losses
        if total == 0:
            print(f"[INFO] No se encontraron partidos en {surface} para {player_name}")
            return None

        return {
            "wins": wins,
            "losses": losses,
            "winrate": round((wins / total) * 100, 2)
        }
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de conexión al obtener winrate: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Error inesperado al obtener winrate: {e}")
        return None

def fetch_head_to_head(player1: str, player2: str) -> dict:
    """
    Devuelve el historial de enfrentamientos (head-to-head) entre dos jugadores usando la API de tenis.
    """
    if not RAPIDAPI_KEY:
        print("[ERROR] RAPIDAPI_KEY no está configurada")
        return None
    
    url = f"https://{RAPIDAPI_HOST}/tennis/v2/matches/h2h"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    params = {
        "player1": player1,
        "player2": player2
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code != 200:
            print(f"[ERROR] Fallo en H2H: {response.status_code} - {response.text}")
            return None

        data = response.json()
        matches = data.get("matches", [])

        if not matches:
            print(f"[INFO] No se encontraron enfrentamientos entre {player1} y {player2}")
            return None

        wins_p1 = 0
        wins_p2 = 0
        recent_matches = []

        for match in matches:
            winner = match.get("winner", {}).get("name", "")
            if player1.lower() in winner.lower():
                wins_p1 += 1
            elif player2.lower() in winner.lower():
                wins_p2 += 1

            recent_matches.append({
                "date": match.get("date", "N/D")[:10],
                "tournament": match.get("tournament", {}).get("name", "N/D"),
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
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de conexión al obtener H2H: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Error inesperado al obtener H2H: {e}")
        return None


def parse_injury_table(soup, table_id):
    rows = soup.select(f"div#injuries > table:nth-of-type({table_id}) tr")
    data = []
    for row in rows[1:]:  # saltar encabezado
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        date_str = cols[0].text.strip()
        try:
            date = datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            continue

        if date.year < datetime.today().year - 1:
            continue

        player = cols[1].text.strip()
        tournament = cols[2].text.strip()
        reason = cols[3].text.strip()
        data.append({
            "date": date.strftime("%Y-%m-%d"),
            "player": player,
            "tournament": tournament,
            "status": "injured" if table_id == 1 else "returning",
            "reason": reason
        })
    return data


def fetch_injury_reports(player_name: str) -> list:
    """
    Recupera las lesiones o retornos de un jugador específico desde TennisExplorer.
    """
    url = "https://www.tennisexplorer.com/injured/"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            print(f"[ERROR] No se pudo acceder a TennisExplorer: {res.status_code}")
            return []

        soup = BeautifulSoup(res.content, "html.parser")
        all_entries = parse_injury_table(soup, 1) + parse_injury_table(soup, 2)

        # Filtrar por coincidencia de nombre parcial (ignorando mayúsculas/minúsculas)
        filtered = [
            entry for entry in all_entries
            if player_name.lower() in entry["player"].lower()
        ]

        if not filtered:
            print(f"[INFO] No se encontraron lesiones para {player_name}")
            
        return filtered
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de conexión al obtener lesiones: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Error inesperado al obtener lesiones: {e}")
        return []


def test_player_utils():
    """
    Función de prueba para verificar que las utilidades de players funcionan correctamente.
    """
    print("=== PRUEBA DE PLAYER UTILS (RAPIDAPI) ===")
    
    # Probar configuración de API
    if not RAPIDAPI_KEY:
        print("❌ RAPIDAPI_KEY no está configurada")
        print("   Configura la variable de entorno RAPIDAPI_KEY")
        return False
    else:
        print("✅ RAPIDAPI_KEY está configurada")
    
    # Probar ranking ATP
    print("\n--- Probando fetch_atp_rankings ---")
    rankings = fetch_atp_rankings()
    if rankings:
        print(f"✅ Ranking ATP obtenido: {len(rankings)} jugadores")
        for i, player in enumerate(rankings[:3]):
            print(f"   {i+1}. {player['name']} ({player['country']}) - {player['points']} pts")
    else:
        print("❌ No se pudo obtener el ranking ATP")
    
    # Probar búsqueda de jugador
    print("\n--- Probando fetch_player_id ---")
    test_player = "Carlos Alcaraz"
    player_id = fetch_player_id(test_player)
    if player_id:
        print(f"✅ Jugador encontrado: {test_player} (ID: {player_id})")
    else:
        print(f"❌ No se pudo encontrar el jugador: {test_player}")
    
    # Probar partidos recientes
    print("\n--- Probando fetch_recent_matches ---")
    matches = fetch_recent_matches(test_player, 3)
    if matches:
        print(f"✅ Partidos recientes obtenidos: {len(matches)} partidos")
        for match in matches[:2]:
            print(f"   {match['date']}: vs {match['opponent']} - {match['result']}")
    else:
        print(f"❌ No se pudieron obtener partidos recientes para {test_player}")
    
    # Probar winrate por superficie
    print("\n--- Probando fetch_surface_winrate ---")
    stats = fetch_surface_winrate(test_player, "hard")
    if stats:
        print(f"✅ Winrate en hard: {stats['winrate']}% ({stats['wins']}W/{stats['losses']}L)")
    else:
        print(f"❌ No se pudo obtener winrate para {test_player}")
    
    # Probar H2H
    print("\n--- Probando fetch_head_to_head ---")
    h2h = fetch_head_to_head(test_player, "Novak Djokovic")
    if h2h:
        print(f"✅ H2H encontrado: {h2h['total']} partidos")
        print(f"   {test_player}: {h2h['wins_p1']} victorias")
        print(f"   Djokovic: {h2h['wins_p2']} victorias")
    else:
        print(f"❌ No se pudo obtener H2H entre {test_player} y Djokovic")
    
    # Probar lesiones
    print("\n--- Probando fetch_injury_reports ---")
    injuries = fetch_injury_reports(test_player)
    if injuries:
        print(f"✅ Lesiones encontradas: {len(injuries)} registros")
        for injury in injuries[:2]:
            print(f"   {injury['date']}: {injury['status']} - {injury['reason']}")
    else:
        print(f"❌ No se encontraron lesiones para {test_player}")
    
    print("\n=== FIN DE PRUEBA ===")
    return True

if __name__ == "__main__":
    test_player_utils()
