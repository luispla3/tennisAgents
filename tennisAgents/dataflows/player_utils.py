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
        
        print(f"[DEBUG] Jugadores disponibles en API: {len(players_data)}")
        
        for i, player_data in enumerate(players_data[:20]):  # Top 20
            # Extraer los datos que necesitamos: ID, nombre, puntos y posición
            player_info = player_data.get("player", {})
            player_id = player_info.get("id", "N/D")
            player_name = player_info.get("name", "N/D")
            points = player_data.get("point", "N/D")
            position = player_data.get("position", "N/D")
            
            rankings.append({
                "id": player_id,
                "name": player_name,
                "point": points,
                "position": position
            })
            
            print(f"[DEBUG] Jugador procesado: {position}. {player_name} (ID: {player_id}) - {points} pts")

        print(f"[INFO] Ranking ATP obtenido exitosamente: {len(rankings)} jugadores")
        return rankings
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de conexión al obtener ranking ATP: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Error inesperado al obtener ranking ATP: {e}")
        return []



def fetch_recent_matches(player_id: int, opponent_id: int, num_matches: int = 30) -> list:
    """
    Obtiene los partidos recientes entre dos jugadores usando la API de tenis.
    Utiliza el endpoint getH2HMatches de la API ATP/WTA/ITF.
    """
    if not RAPIDAPI_KEY:
        print("[ERROR] RAPIDAPI_KEY no está configurada")
        return []
    
    url = f"https://{RAPIDAPI_HOST}/tennis/v2/atp/h2h/matches/{player_id}/{opponent_id}/"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    params = {}

    try:
        print(f"[DEBUG] Intentando obtener partidos recientes entre jugadores {player_id} y {opponent_id}...")
        print(f"[DEBUG] URL: {url}")
        print(f"[DEBUG] Params: {params}")
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        print(f"[DEBUG] Status code: {response.status_code}")
        
        if response.status_code == 401:
            print("[ERROR] API key inválida o no autorizada")
            return []
        elif response.status_code == 403:
            print("[ERROR] Acceso denegado - verifica tu plan de suscripción")
            return []
        elif response.status_code != 200:
            print(f"[ERROR] Fallo al obtener partidos recientes: {response.status_code}")
            print(f"[DEBUG] Response: {response.text}")
            return []

        data = response.json()
        print(f"[DEBUG] Datos recibidos de RapidAPI")
        print(f"[DEBUG] Response keys: {list(data.keys()) if isinstance(data, dict) else 'No es dict'}")
        
        matches = data.get("data", [])
        
        if not matches:
            print(f"[INFO] No se encontraron partidos entre los jugadores {player_id} y {opponent_id}")
            return []
        
        print(f"[DEBUG] Partidos encontrados: {len(matches)}")
        
        # Procesar los partidos y limitar al número solicitado
        processed_matches = []
        for i, match in enumerate(matches[:num_matches]):
            print(f"[DEBUG] Procesando partido {i+1}: {match}")
            
            # Extraer datos según la estructura de la API
            match_date = match.get("date", "")
            
            # Obtener información de los jugadores
            player1_info = match.get("player1", {})
            player2_info = match.get("player2", {})
            
            # Determinar el ganador basado en el resultado
            result = match.get("result", "")
            winner_name = "N/D"
            opponent_name = "N/D"
            
            # Si hay resultado, intentar determinar el ganador
            if result and player1_info and player2_info:
                # Por ahora, asumimos que el primer jugador es el ganador
                # En una implementación más completa, analizaríamos el resultado
                winner_name = player1_info.get("name", "N/D")
                opponent_name = player2_info.get("name", "N/D")
            
            processed_matches.append({
                "date": match_date[:10] if match_date else "N/D",
                "tournament": f"Tournament ID: {match.get('tournamentId', 'N/D')}",
                "opponent": opponent_name,
                "result": result,
                "surface": "N/D",  # La API no parece incluir superficie en este endpoint
                "winner": winner_name
            })
            
            print(f"[DEBUG] Partido procesado: {match_date[:10]} | Tournament ID: {match.get('tournamentId', 'N/D')} | vs {opponent_name} | Resultado: {result}")

        print(f"[INFO] Partidos recientes obtenidos exitosamente: {len(processed_matches)} partidos")
        return processed_matches
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de conexión al obtener partidos recientes: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Error inesperado al obtener partidos recientes: {e}")
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


