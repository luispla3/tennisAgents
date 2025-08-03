import requests
import os
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Usar la nueva API de tenis ATP/WTA/ITF de RapidAPI
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = "tennis-api-atp-wta-itf.p.rapidapi.com"


def scrape_injured_players(page_url: str) -> list:
    """
    Scrapes injured players data from a single page of TennisExplorer.
    
    Args:
        page_url: URL of the page to scrape
        
    Returns:
        List of dictionaries containing injured player data
    """
    try:
        print(f"[DEBUG] Scraping injured players from: {page_url}")
        
        # Headers to mimic a real browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(page_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"[ERROR] Failed to fetch page {page_url}: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the table with injured players data
        table = soup.find('table', class_='result flags injured')
        
        if not table:
            print(f"[ERROR] Could not find injured players table on page {page_url}")
            return []
        
        injured_players = []
        
        # Find all table rows (tr elements)
        rows = table.find_all('tr')
        
        for row in rows:
            # Skip header row if it exists
            if row.find('th'):
                continue
                
            # Get all table data cells
            cells = row.find_all('td')
            
            if len(cells) >= 4:  # We expect at least 4 columns: date, name, tournament, reason
                try:
                    # Extract date
                    date_cell = cells[0]
                    date_text = date_cell.get_text(strip=True)
                    
                    # Extract player name and link
                    name_cell = cells[1]
                    player_link = name_cell.find('a')
                    player_name = player_link.get_text(strip=True) if player_link else name_cell.get_text(strip=True)
                    player_url = player_link.get('href') if player_link else None
                    
                    # Extract tournament
                    tournament_cell = cells[2]
                    tournament_text = tournament_cell.get_text(strip=True)
                    
                    # Extract reason
                    reason_cell = cells[3]
                    reason_text = reason_cell.get_text(strip=True)
                    
                    # Parse date
                    try:
                        parsed_date = datetime.strptime(date_text, '%d.%m.%Y')
                        formatted_date = parsed_date.strftime('%Y-%m-%d')
                    except ValueError:
                        formatted_date = date_text
                    
                    player_data = {
                        'date': formatted_date,
                        'player_name': player_name,
                        'player_url': player_url,
                        'tournament': tournament_text,
                        'reason': reason_text,
                        'source_page': page_url
                    }
                    
                    injured_players.append(player_data)
                    
                except Exception as e:
                    print(f"[WARNING] Error processing row: {e}")
                    continue
        
        print(f"[INFO] Scraped {len(injured_players)} injured players from {page_url}")
        return injured_players
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Network error scraping {page_url}: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Unexpected error scraping {page_url}: {e}")
        return []


def scrape_returning_players(page_url: str) -> list:
    """
    Scrapes returning players data from TennisExplorer.
    
    Args:
        page_url: URL of the page to scrape
        
    Returns:
        List of dictionaries containing returning player data
    """
    try:
        print(f"[DEBUG] Scraping returning players from: {page_url}")
        
        # Headers to mimic a real browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(page_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"[ERROR] Failed to fetch page {page_url}: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the table with returning players data
        table = soup.find('table', class_='result flags injured')
        
        if not table:
            print(f"[ERROR] Could not find returning players table on page {page_url}")
            return []
        
        returning_players = []
        
        # Find all table rows (tr elements)
        rows = table.find_all('tr')
        
        for row in rows:
            # Skip header row if it exists
            if row.find('th'):
                continue
                
            # Get all table data cells
            cells = row.find_all('td')
            
            if len(cells) >= 3:  # We expect at least 3 columns: date, name, tournament
                try:
                    # Extract date
                    date_cell = cells[0]
                    date_text = date_cell.get_text(strip=True)
                    
                    # Extract player name and link
                    name_cell = cells[1]
                    player_link = name_cell.find('a')
                    player_name = player_link.get_text(strip=True) if player_link else name_cell.get_text(strip=True)
                    player_url = player_link.get('href') if player_link else None
                    
                    # Extract tournament
                    tournament_cell = cells[2]
                    tournament_text = tournament_cell.get_text(strip=True)
                    
                    # Parse date
                    try:
                        parsed_date = datetime.strptime(date_text, '%d.%m.%Y')
                        formatted_date = parsed_date.strftime('%Y-%m-%d')
                    except ValueError:
                        formatted_date = date_text
                    
                    player_data = {
                        'date': formatted_date,
                        'player_name': player_name,
                        'player_url': player_url,
                        'tournament': tournament_text,
                        'status': 'returned',
                        'source_page': page_url
                    }
                    
                    returning_players.append(player_data)
                    
                except Exception as e:
                    print(f"[WARNING] Error processing returning player row: {e}")
                    continue
        
        print(f"[INFO] Scraped {len(returning_players)} returning players from {page_url}")
        return returning_players
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Network error scraping {page_url}: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Unexpected error scraping {page_url}: {e}")
        return []


def fetch_injury_reports() -> dict:
    """
    Gets injury reports by scraping TennisExplorer for both injured and returning players.
    
    Returns:
        Dictionary containing 'injured_players' and 'returning_players' lists
    """
    print("[INFO] Starting injury reports scraping...")
    
    # Base URLs for injured players (5 pages)
    injured_urls = [
        "https://www.tennisexplorer.com/list-players/injured/?page=1",
        "https://www.tennisexplorer.com/list-players/injured/?page=2", 
        "https://www.tennisexplorer.com/list-players/injured/?page=3",
        "https://www.tennisexplorer.com/list-players/injured/?page=4",
        "https://www.tennisexplorer.com/list-players/injured/?page=5"
    ]
    
    # URL for returning players (1 page)
    returning_url = "https://www.tennisexplorer.com/list-players/return-from-injury/"
    
    all_injured_players = []
    
    # Scrape all pages for injured players
    for url in injured_urls:
        print(f"[DEBUG] Scraping injured players from page: {url}")
        page_players = scrape_injured_players(url)
        all_injured_players.extend(page_players)
        
        # Add a small delay between requests to be respectful
        import time
        time.sleep(1)
    
    print(f"[INFO] Total injured players scraped: {len(all_injured_players)}")
    
    # Scrape returning players
    print(f"[DEBUG] Scraping returning players from: {returning_url}")
    returning_players = scrape_returning_players(returning_url)
    print(f"[INFO] Total returning players scraped: {len(returning_players)}")
    
    return {
        'injured_players': all_injured_players,
        'returning_players': returning_players,
        'total_injured': len(all_injured_players),
        'total_returning': len(returning_players),
        'scraped_at': datetime.now().isoformat()
    }



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



def fetch_surface_winrate(player_id: int, surface: str) -> dict:
    """
    Devuelve el winrate de un jugador en una superficie dada usando la API de tenis.
    Utiliza el endpoint getPlayerSurfaceSummary de la API ATP/WTA/ITF.
    """
    if not RAPIDAPI_KEY:
        print("[ERROR] RAPIDAPI_KEY no está configurada")
        return None
    
    # Mapeo de superficies a courtId según la documentación
    surface_mapping = {
        "hard": 1,
        "clay": 2, 
        "i.hard": 3,
        "grass": 5
    }
    
    court_id = surface_mapping.get(surface.lower())
    if not court_id:
        print(f"[ERROR] Superficie '{surface}' no soportada. Superficies válidas: hard, clay, i.hard, grass")
        return None

    url = f"https://{RAPIDAPI_HOST}/tennis/v2/atp/player/surface-summary/{player_id}"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    params = {}

    try:
        print(f"[DEBUG] Intentando obtener winrate para jugador {player_id} en superficie {surface}...")
        print(f"[DEBUG] URL: {url}")
        print(f"[DEBUG] Params: {params}")
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        print(f"[DEBUG] Status code: {response.status_code}")
        
        if response.status_code == 401:
            print("[ERROR] API key inválida o no autorizada")
            return None
        elif response.status_code == 403:
            print("[ERROR] Acceso denegado - verifica tu plan de suscripción")
            return None
        elif response.status_code != 200:
            print(f"[ERROR] Fallo al obtener winrate: {response.status_code}")
            print(f"[DEBUG] Response: {response.text}")
            return None

        data = response.json()
        print(f"[DEBUG] Datos recibidos de RapidAPI")
        print(f"[DEBUG] Response keys: {list(data.keys()) if isinstance(data, dict) else 'No es dict'}")
        
        surface_data = data.get("data", [])
        
        if not surface_data:
            print(f"[INFO] No se encontraron datos de superficie para el jugador {player_id}")
            return None
        
        print(f"[DEBUG] Datos de superficie encontrados: {len(surface_data)} años")
        
        # Buscar datos para la superficie específica en el año más reciente
        total_wins = 0
        total_losses = 0
        
        for year_data in surface_data:
            year = year_data.get("year", 0)
            surfaces = year_data.get("surfaces", [])
            
            print(f"[DEBUG] Procesando año {year} con {len(surfaces)} superficies")
            
            for surface_info in surfaces:
                if surface_info.get("courtId") == court_id:
                    wins = surface_info.get("courtWins", 0)
                    losses = surface_info.get("courtLosses", 0)
                    court_name = surface_info.get("court", "N/D")
                    
                    print(f"[DEBUG] Superficie {court_name}: {wins} victorias, {losses} derrotas")
                    
                    total_wins += wins
                    total_losses += losses

        total_matches = total_wins + total_losses
        if total_matches == 0:
            print(f"[INFO] No se encontraron partidos en {surface} para el jugador {player_id}")
            return None

        winrate = round((total_wins / total_matches) * 100, 2)
        
        print(f"[INFO] Winrate calculado: {total_wins} victorias, {total_losses} derrotas = {winrate}%")
        
        return {
            "wins": total_wins,
            "losses": total_losses,
            "winrate": winrate
        }
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de conexión al obtener winrate: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Error inesperado al obtener winrate: {e}")
        return None


def fetch_head_to_head(player1: int, player2: int) -> dict:
    """
    Devuelve las estadísticas head-to-head entre dos jugadores usando la API de tenis.
    Basado en la documentación del endpoint getH2HStats.
    """
    if not RAPIDAPI_KEY:
        print("[ERROR] RAPIDAPI_KEY no está configurada")
        return None
    
    url = f"https://{RAPIDAPI_HOST}/tennis/v2/atp/h2h/stats/{player1}/{player2}/"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 401:
            print("[ERROR] API key inválida o no autorizada")
            return None
        elif response.status_code == 403:
            print("[ERROR] Acceso denegado - verifica tu plan de suscripción")
            return None
        elif response.status_code != 200:
            print(f"[ERROR] Fallo en H2H: {response.status_code} - {response.text}")
            return None

        data = response.json()
        
        if not data or "data" not in data:
            print(f"[INFO] No se encontraron estadísticas H2H entre jugadores {player1} y {player2}")
            return None

        h2h_data = data["data"]
        matches_count = h2h_data.get("matchesCount", "0")
        
        # Extraer estadísticas de ambos jugadores
        player1_stats = None
        player2_stats = None
        
        if "player1Stats" in h2h_data:
            player1_stats = h2h_data["player1Stats"]
        if "player2Stats" in h2h_data:
            player2_stats = h2h_data["player2Stats"]

        result = {
            "matches_count": matches_count,
            "player1_stats": player1_stats,
            "player2_stats": player2_stats,
            "raw_data": h2h_data
        }
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de conexión al obtener H2H: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Error inesperado al obtener H2H: {e}")
        return None




