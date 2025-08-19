from openai import OpenAI
import requests
import os
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

from tennisAgents.dataflows.config import get_config

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
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the table with injured players data
        table = soup.find('table', class_='result flags injured')
        
        if not table:
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
                    continue
        
        return injured_players
        
    except requests.exceptions.RequestException as e:
        return []
    except Exception as e:
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
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the table with returning players data
        table = soup.find('table', class_='result flags injured')
        
        if not table:
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
                    continue
        
        return returning_players
        
    except requests.exceptions.RequestException as e:
        return []
    except Exception as e:
        return []


def fetch_injury_reports() -> str:
    """
    Gets injury reports using OpenAI instead of web scraping.
    
    Returns:
        String containing injury reports information
    """
    config = get_config()
    client = OpenAI(base_url=config["backend_url"])

    try:
        response = client.responses.create(
            model=config["quick_think_llm"],
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Busca información actualizada sobre jugadores de tenis lesionados y jugadores que están regresando de lesiones. Incluye nombres, tipos de lesiones, fechas, torneos afectados, y estado actual de recuperación. Enfócate en jugadores relevantes del circuito ATP.",
                        }
                    ],
                }
            ],
            text={"format": {"type": "text"}},
            reasoning={},
            tools=[
                {
                    "type": "web_search_preview",
                    "user_location": {"type": "approximate"},
                    "search_context_size": "medium",
                }
            ],
            temperature=1,
            max_output_tokens=4096,
            top_p=1,
            store=True,
        )
        return response.output[1].content[0].text
    except Exception as e:
        return f"Error al obtener reportes de lesiones: {str(e)}"



def fetch_atp_rankings() -> list:
    config = get_config()
    client = OpenAI(base_url=config["backend_url"])

    response = client.responses.create(
        model=config["quick_think_llm"],
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Busca el top 100 del ranking ATP y devuelve una lista de jugadores con su nombre, ranking y puntos. El formato debe ser una lista de diccionarios con las claves 'name', 'ranking' y 'points'.",
                    }
                ],
            }
        ],
        text={"format": {"type": "text"}},
        reasoning={},
        tools=[
            {
                "type": "web_search_preview",
                "user_location": {"type": "approximate"},
                "search_context_size": "low",
            }
        ],
        temperature=1,
        max_output_tokens=4096,
        top_p=1,
        store=True,
    )

    return response.output[1].content[0].text



def fetch_recent_matches(player1_name: str, player2_name: str, num_matches: int = 30) -> str:
    """
    Obtiene los partidos recientes entre dos jugadores usando OpenAI.
    """
    config = get_config()
    client = OpenAI(base_url=config["backend_url"])

    try:
        response = client.responses.create(
            model=config["quick_think_llm"],
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"Busca información sobre los últimos {num_matches} partidos jugados por {player1_name} y {player2_name}. Incluye fechas, torneos, resultados, superficies y estadísticas relevantes. Devuelve un análisis detallado de su rendimiento reciente.",
                        }
                    ],
                }
            ],
            text={"format": {"type": "text"}},
            reasoning={},
            tools=[
                {
                    "type": "web_search_preview",
                    "user_location": {"type": "approximate"},
                    "search_context_size": "medium",
                }
            ],
            temperature=1,
            max_output_tokens=4096,
            top_p=1,
            store=True,
        )
        return response.output[1].content[0].text
    except Exception as e:
        return f"Error al obtener partidos recientes: {str(e)}"



def fetch_surface_winrate(player_name: str, surface: str) -> str:
    """
    Devuelve el winrate de un jugador en una superficie dada usando OpenAI.
    """
    config = get_config()
    client = OpenAI(base_url=config["backend_url"])

    try:
        response = client.responses.create(
            model=config["quick_think_llm"],
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"Busca estadísticas específicas sobre el rendimiento de {player_name} en superficie {surface} (clay, hard, grass). Incluye winrate, partidos ganados/perdidos, títulos, y rendimiento histórico en esta superficie. Devuelve datos cuantitativos y análisis cualitativo.",
                        }
                    ],
                }
            ],
            text={"format": {"type": "text"}},
            reasoning={},
            tools=[
                {
                    "type": "web_search_preview",
                    "user_location": {"type": "approximate"},
                    "search_context_size": "medium",
                }
            ],
            temperature=1,
            max_output_tokens=4096,
            top_p=1,
            store=True,
        )
        return response.output[1].content[0].text
    except Exception as e:
        return f"Error al obtener winrate en superficie: {str(e)}"


def fetch_head_to_head(player1_name: str, player2_name: str) -> str:
    """
    Devuelve las estadísticas head-to-head entre dos jugadores usando OpenAI.
    """
    config = get_config()
    client = OpenAI(base_url=config["backend_url"])

    try:
        response = client.responses.create(
            model=config["quick_think_llm"],
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"Busca el historial completo de enfrentamientos (head-to-head) entre {player1_name} y {player2_name}. Incluye total de partidos, victorias de cada uno, fechas, torneos, superficies, y análisis de patrones en sus enfrentamientos. Devuelve estadísticas detalladas y contexto histórico.",
                        }
                    ],
                }
            ],
            text={"format": {"type": "text"}},
            reasoning={},
            tools=[
                {
                    "type": "web_search_preview",
                    "user_location": {"type": "approximate"},
                    "search_context_size": "medium",
                }
            ],
            temperature=1,
            max_output_tokens=4096,
            top_p=1,
            store=True,
        )
        return response.output[1].content[0].text
    except Exception as e:
        return f"Error al obtener head-to-head: {str(e)}"




