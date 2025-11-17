"""
Match Live Utilities - Herramientas para obtener datos en tiempo real de partidos de tenis usando Sportradar API
"""

import os
import json
import time
import requests
import unicodedata
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, Any, Optional, List

load_dotenv()

"""
Usuario solicita partido
         ↓
fetch_match_live_data(player_a, player_b, tournament)
         ↓
fetch_live_summaries(include_all_statuses=False)  # Intento 1: solo "live"
         ↓
find_match_in_summaries()  → usa player_name_matches()
         ↓
    ¿Encontrado?
    NO → fetch_live_summaries(include_all_statuses=True)  # Intento 2: todos los estados
         ↓
    SÍ → format_match_data_structured()
         ↓
    Retorna datos estructurados
"""

def get_sportradar_api_key() -> str:
    """
    Obtiene la API key de Sportradar desde las variables de entorno.
    
    Returns:
        str: API key de Sportradar
        
    Raises:
        ValueError: Si no se encuentra la API key
    """
    api_key = os.getenv("SPORTRADAR_API_KEY")
    if not api_key:
        raise ValueError("SPORTRADAR_API_KEY no está configurada en las variables de entorno")
    return api_key


def normalize_name(name: str) -> str:
    """
    Normaliza un nombre eliminando acentos y convirtiendo a minúsculas para comparación.
    
    Args:
        name (str): Nombre a normalizar
    
    Returns:
        str: Nombre normalizado sin acentos y en minúsculas
    """
    # Eliminar acentos y caracteres especiales
    nfkd_form = unicodedata.normalize('NFKD', name)
    normalized = ''.join([c for c in nfkd_form if not unicodedata.combining(c)])
    return normalized.lower().strip()


def player_name_matches(api_name: str, search_name: str, debug: bool = False) -> bool:
    """
    Verifica si un nombre de jugador de la API coincide con el nombre buscado.
    
    La API de Sportradar devuelve nombres en formato "Apellido, Nombre" o variaciones.
    Esta función maneja diferentes formatos y normaliza los nombres para comparación.
    
    Args:
        api_name (str): Nombre del jugador como viene de la API (ej: "Djokovic, Novak")
        search_name (str): Nombre buscado (ej: "Djokovic" o "Novak Djokovic")
        debug (bool): Si True, imprime información de debug
    
    Returns:
        bool: True si los nombres coinciden
    """
    # Normalizar ambos nombres
    api_normalized = normalize_name(api_name)
    search_normalized = normalize_name(search_name)
    
    if debug:
        print(f"          Comparando: API='{api_normalized}' vs Search='{search_normalized}'")
    
    # Estrategia 1: El nombre buscado está contenido en el nombre de la API
    if search_normalized in api_normalized:
        if debug:
            print(f"          ✓ Match: nombre buscado contenido en API")
        return True
    
    # Estrategia 2: El nombre de la API está contenido en el nombre buscado
    if api_normalized in search_normalized:
        if debug:
            print(f"          ✓ Match: nombre API contenido en búsqueda")
        return True
    
    # Estrategia 3: Si el nombre de la API tiene formato "Apellido, Nombre", intentar invertirlo
    if ',' in api_name:
        parts = [normalize_name(p.strip()) for p in api_name.split(',')]
        # Probar "Nombre Apellido"
        reversed_name = ' '.join(reversed(parts))
        if debug:
            print(f"          Formato invertido: '{reversed_name}'")
        
        if search_normalized in reversed_name or reversed_name in search_normalized:
            if debug:
                print(f"          ✓ Match: formato invertido")
            return True
    
    # Estrategia 4: Comparar palabras individuales (apellidos principalmente)
    search_words = set(search_normalized.split())
    api_words = set(api_normalized.replace(',', ' ').split())
    
    # Si hay palabras significativas en común (3+ caracteres)
    significant_search_words = {w for w in search_words if len(w) >= 3}
    significant_api_words = {w for w in api_words if len(w) >= 3}
    
    common_words = significant_search_words & significant_api_words
    
    if debug:
        print(f"          Palabras búsqueda: {significant_search_words}")
        print(f"          Palabras API: {significant_api_words}")
        print(f"          Palabras comunes: {common_words}")
    
    # Si tienen al menos una palabra significativa en común, considerar match
    if common_words:
        if debug:
            print(f"          ✓ Match: palabras comunes encontradas")
        return True
    
    if debug:
        print(f"          ✗ No match")
    
    return False


def fetch_live_summaries(include_all_statuses: bool = False) -> Dict[str, Any]:
    """
    Obtiene todos los resúmenes de partidos en vivo desde la API de Sportradar.
    
    Args:
        include_all_statuses (bool): Si True, incluye partidos en cualquier estado (not_started, live, ended, closed).
                                      Si False, solo incluye partidos con estado "live"
    
    Returns:
        Dict[str, Any]: Diccionario con:
            - success (bool): Si la operación fue exitosa
            - data (Dict): Datos completos de la API
            - total_matches (int): Número total de partidos
            - fetched_at (str): Timestamp de la consulta
            - error (str): Mensaje de error si falló
    """
    try:
        api_key = get_sportradar_api_key()
        
        url = "https://api.sportradar.com/tennis/trial/v3/en/schedules/live/summaries.json"
        headers = {
            "accept": "application/json",
            "x-api-key": api_key
        }
        
        print(f"[INFO] Consultando Sportradar Live Summaries API...")
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        summaries = data.get("summaries", [])
        
        # Filtrar por estado si se solicita
        if not include_all_statuses:
            original_count = len(summaries)
            summaries = [s for s in summaries if s.get("sport_event_status", {}).get("status") == "live"]
            print(f"[INFO] Filtrados {original_count - len(summaries)} partidos no-live")
            # Actualizar los summaries en data
            data["summaries"] = summaries
        
        print(f"[SUCCESS] Se obtuvieron {len(summaries)} partidos")
        
        return {
            "success": True,
            "data": data,
            "total_matches": len(summaries),
            "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except ValueError as ve:
        print(f"[ERROR] Error de configuración: {str(ve)}")
        return {
            "success": False,
            "error": str(ve),
            "data": {},
            "total_matches": 0,
            "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "note": "Verifica que SPORTRADAR_API_KEY esté configurada en el archivo .env"
        }
        
    except requests.exceptions.HTTPError as http_err:
        print(f"[ERROR] Error HTTP al consultar Sportradar: {str(http_err)}")
        return {
            "success": False,
            "error": f"Error HTTP: {str(http_err)}",
            "data": {},
            "total_matches": 0,
            "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "note": f"Código de estado: {response.status_code if 'response' in locals() else 'N/A'}"
        }
        
    except requests.exceptions.RequestException as req_err:
        print(f"[ERROR] Error de conexión al consultar Sportradar: {str(req_err)}")
        return {
            "success": False,
            "error": f"Error de conexión: {str(req_err)}",
            "data": {},
            "total_matches": 0,
            "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        print(f"[ERROR] Error inesperado: {str(e)}")
        return {
            "success": False,
            "error": f"Error inesperado: {str(e)}",
            "data": {},
            "total_matches": 0,
            "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


def tournament_name_matches(api_tournament: str, search_tournament: str, debug: bool = False) -> bool:
    """
    Verifica si un nombre de torneo de la API coincide con el nombre buscado.
    
    Maneja:
    - Variaciones de idioma (Masculino/Men, Femenino/Women, Viena/Vienna)
    - Nombres parciales (Roanne vs ATP Challenger Roanne, France)
    - Diferentes formatos
    
    Args:
        api_tournament (str): Nombre del torneo como viene de la API
        search_tournament (str): Nombre del torneo buscado
        debug (bool): Si True, imprime información de debug
    
    Returns:
        bool: True si los nombres coinciden
    """
    # Normalizar ambos nombres
    api_normalized = normalize_name(api_tournament)
    search_normalized = normalize_name(search_tournament)
    
    if debug:
        print(f"        Comparando torneos: API='{api_normalized}' vs Search='{search_normalized}'")
    
    # Mapeo de traducciones y variaciones comunes de ciudades
    translations = {
        'masculino': 'men',
        'femenino': 'women',
        'mens': 'men',
        'womens': 'women',
        'singles': 'individual',
        'doubles': 'dobles',
        # Ciudades con variaciones de nombre
        'viena': 'vienna',
        'wien': 'vienna',
        'munich': 'munchen',
        'praga': 'prague',
        'praha': 'prague',
        'moscu': 'moscow',
        'moskva': 'moscow',
    }
    
    # Aplicar traducciones
    for spanish, english in translations.items():
        search_normalized = search_normalized.replace(spanish, english)
        api_normalized = api_normalized.replace(spanish, english)
    
    if debug:
        print(f"        Después de traducciones: API='{api_normalized}' vs Search='{search_normalized}'")
    
    # Estrategia 1: El nombre buscado está contenido en el nombre de la API
    if search_normalized in api_normalized:
        if debug:
            print(f"        [OK] Match: nombre buscado contenido en API")
        return True
    
    # Estrategia 2: El nombre de la API está contenido en la búsqueda
    if api_normalized in search_normalized:
        if debug:
            print(f"        [OK] Match: nombre API contenido en búsqueda")
        return True
    
    # Estrategia 3: Extraer palabras clave significativas y verificar que la mayoría coincidan
    search_words = [w for w in search_normalized.split() if len(w) >= 3]
    api_words = set([w for w in api_normalized.split() if len(w) >= 3])
    
    if debug:
        print(f"        Palabras busqueda: {search_words}")
        print(f"        Palabras API: {api_words}")
    
    # Si al menos el 50% de las palabras clave están presentes, considerar match
    if search_words:
        matches = sum(1 for word in search_words if word in api_words)
        match_ratio = matches / len(search_words)
        if debug:
            print(f"        Match ratio: {match_ratio:.2f} ({matches}/{len(search_words)})")
        if match_ratio >= 0.5:
            if debug:
                print(f"        [OK] Match: ratio suficiente")
            return True
    
    if debug:
        print(f"        [X] No match")
    
    return False


def find_match_in_summaries(
    summaries_data: Dict[str, Any],
    player_a: str,
    player_b: str,
    tournament: Optional[str] = None,
    debug: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Busca un partido específico dentro de los resúmenes de partidos en vivo.
    
    Args:
        summaries_data (Dict[str, Any]): Datos obtenidos de fetch_live_summaries()
        player_a (str): Nombre del primer jugador
        player_b (str): Nombre del segundo jugador
        tournament (Optional[str]): Nombre del torneo (opcional para filtrar)
        debug (bool): Si True, imprime información de debug detallada
    
    Returns:
        Optional[Dict[str, Any]]: Datos del partido encontrado o None si no se encuentra
    """
    if not summaries_data.get("success"):
        return None
    
    summaries = summaries_data.get("data", {}).get("summaries", [])
    
    print(f"\n[INFO] Buscando partido entre '{player_a}' y '{player_b}'")
    if tournament:
        print(f"[INFO] Filtrando por torneo: '{tournament}'")
    
    # DEBUG: Mostrar todos los partidos disponibles
    if debug and summaries:
        print(f"\n[DEBUG] ===== PARTIDOS EN VIVO DISPONIBLES ({len(summaries)}) =====")
        for idx, summary in enumerate(summaries, 1):
            sport_event = summary.get("sport_event", {})
            competitors = sport_event.get("competitors", [])
            competition_name = sport_event.get("sport_event_context", {}).get("competition", {}).get("name", "N/A")
            
            if len(competitors) == 2:
                player1 = competitors[0].get("name", "N/A")
                player2 = competitors[1].get("name", "N/A")
                print(f"  [{idx}] {player1} vs {player2}")
                print(f"      Torneo: {competition_name}")
        print(f"[DEBUG] ==========================================\n")
    
    # Buscar el partido
    for idx, summary in enumerate(summaries, 1):
        sport_event = summary.get("sport_event", {})
        competitors = sport_event.get("competitors", [])
        
        # Verificar si tenemos exactamente 2 competidores
        if len(competitors) != 2:
            continue
        
        competitor_names = [comp.get("name", "") for comp in competitors]
        
        if debug:
            print(f"[DEBUG] Comparando partido {idx}: {competitor_names[0]} vs {competitor_names[1]}")
        
        # Verificar si ambos jugadores están en el partido
        player_a_matches = [player_name_matches(name, player_a, debug=debug) for name in competitor_names]
        player_b_matches = [player_name_matches(name, player_b, debug=debug) for name in competitor_names]
        
        player_a_found = any(player_a_matches)
        player_b_found = any(player_b_matches)
        
        if debug:
            print(f"        Player A '{player_a}' encontrado: {player_a_found}")
            print(f"        Player B '{player_b}' encontrado: {player_b_found}")
        
        if player_a_found and player_b_found:
            # Si se especificó torneo, verificar que coincida
            if tournament:
                competition_name = sport_event.get("sport_event_context", {}).get("competition", {}).get("name", "")
                
                tournament_matches = tournament_name_matches(competition_name, tournament, debug=debug)
                
                if not tournament_matches:
                    print(f"[INFO] Partido encontrado pero torneo no coincide: '{competition_name}' vs '{tournament}'")
                    continue
            
            print(f"\n[SUCCESS] ✓ Partido encontrado: {competitor_names[0]} vs {competitor_names[1]}")
            return summary
    
    print(f"\n[WARNING] ✗ No se encontró el partido entre '{player_a}' y '{player_b}'")
    print(f"[HINT] Revisa los nombres de los jugadores arriba en la lista de partidos disponibles")
    return None


def list_all_live_matches() -> str:
    """
    Obtiene y lista todos los partidos en vivo disponibles en formato legible.
    
    Útil para debugging cuando no encuentras un partido específico.
    
    Returns:
        str: Lista formateada de todos los partidos en vivo
    """
    try:
        summaries_data = fetch_live_summaries()
        
        if not summaries_data.get("success"):
            return f"Error al obtener partidos: {summaries_data.get('error', 'Error desconocido')}"
        
        summaries = summaries_data.get("data", {}).get("summaries", [])
        
        if not summaries:
            return "No hay partidos en vivo en este momento."
        
        result = f"# PARTIDOS EN VIVO ({len(summaries)} encontrados)\n\n"
        
        for idx, summary in enumerate(summaries, 1):
            sport_event = summary.get("sport_event", {})
            competitors = sport_event.get("competitors", [])
            competition_name = sport_event.get("sport_event_context", {}).get("competition", {}).get("name", "N/A")
            status = summary.get("sport_event_status", {}).get("status", "N/A")
            
            if len(competitors) == 2:
                player1 = competitors[0].get("name", "N/A")
                player2 = competitors[1].get("name", "N/A")
                result += f"{idx}. {player1} vs {player2}\n"
                result += f"   Torneo: {competition_name}\n"
                result += f"   Estado: {status}\n\n"
        
        return result
        
    except Exception as e:
        return f"Error al listar partidos: {str(e)}"


def fetch_match_live_data(player_a: str, player_b: str, tournament: Optional[str] = None, debug: bool = True) -> Dict[str, Any]:
    """
    Obtiene datos en tiempo real de un partido específico usando Sportradar API.
    
    Flujo:
    1. Obtiene todos los partidos en vivo desde Sportradar
    2. Si no se encuentra en partidos "live", busca en todos los estados (programados, finalizados, etc.)
    3. Extrae y estructura la información relevante del partido
    
    Args:
        player_a (str): Nombre del primer jugador
        player_b (str): Nombre del segundo jugador
        tournament (Optional[str]): Nombre del torneo (opcional)
        debug (bool): Si True, imprime información de debug
    
    Returns:
        Dict[str, Any]: Diccionario con:
            - success (bool): Si la operación fue exitosa
            - player_a (str): Nombre del jugador A
            - player_b (str): Nombre del jugador B
            - tournament (str): Nombre del torneo
            - match_data (Dict): Datos estructurados del partido
            - formatted_data (str): Datos formateados en texto para el agente
            - fetched_at (str): Timestamp de la consulta
            - match_status (str): Estado del partido (live, not_started, ended, closed)
            - error (str): Mensaje de error si falló
    """
    try:
        print(f"\n[INFO] Iniciando búsqueda de partido: {player_a} vs {player_b}")
        if tournament:
            print(f"[INFO] Torneo: {tournament}")
        
        # 1. Intentar primero con partidos solo en estado "live"
        print(f"[INFO] Paso 1: Buscando en partidos 'live'...")
        summaries_data = fetch_live_summaries(include_all_statuses=False)
        
        if not summaries_data.get("success"):
            return {
                "success": False,
                "error": summaries_data.get("error", "Error al obtener partidos en vivo"),
                "player_a": player_a,
                "player_b": player_b,
                "tournament": tournament or "N/A",
                "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        # 2. Buscar el partido específico en partidos "live"
        match_summary = find_match_in_summaries(summaries_data, player_a, player_b, tournament, debug=debug)
        
        # 3. Si no se encuentra en "live", intentar con todos los estados
        if not match_summary:
            print(f"\n[WARNING] Partido no encontrado en estado 'live'")
            print(f"[INFO] Paso 2: Buscando en TODOS los estados (not_started, live, ended, closed)...")
            summaries_data_all = fetch_live_summaries(include_all_statuses=True)
            
            if summaries_data_all.get("success"):
                match_summary = find_match_in_summaries(summaries_data_all, player_a, player_b, tournament, debug=debug)
        
        if not match_summary:
            # Generar lista de partidos disponibles para incluir en el error
            available_matches = []
            summaries = summaries_data.get("data", {}).get("summaries", [])
            for summary in summaries[:10]:  # Máximo 10 partidos
                sport_event = summary.get("sport_event", {})
                competitors = sport_event.get("competitors", [])
                status = summary.get("sport_event_status", {}).get("status", "N/A")
                if len(competitors) == 2:
                    p1 = competitors[0].get("name", "N/A")
                    p2 = competitors[1].get("name", "N/A")
                    comp_name = sport_event.get("sport_event_context", {}).get("competition", {}).get("name", "N/A")
                    available_matches.append(f"{p1} vs {p2} ({comp_name}) - Estado: {status}")
            
            available_list = "\n".join(available_matches) if available_matches else "No hay partidos disponibles"
            
            return {
                "success": False,
                "error": f"No se encontró el partido entre {player_a} y {player_b}",
                "player_a": player_a,
                "player_b": player_b,
                "tournament": tournament or "N/A",
                "total_live_matches": summaries_data.get("total_matches", 0),
                "available_matches": available_list,
                "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "note": "El partido podría no estar aún en juego, haber finalizado, o los nombres de los jugadores no coinciden exactamente. Revisa la lista de partidos disponibles arriba."
            }
        
        # 4. Obtener el estado del partido
        match_status = match_summary.get("sport_event_status", {}).get("status", "unknown")
        match_status_info = match_summary.get("sport_event_status", {}).get("match_status", "N/A")
        
        print(f"\n[SUCCESS] Partido encontrado - Estado: {match_status} ({match_status_info})")
        
        # 5. Formatear los datos de manera estructurada
        formatted_data = format_match_data_structured(match_summary)
        
        return {
            "success": True,
            "player_a": player_a,
            "player_b": player_b,
            "tournament": match_summary.get("sport_event", {}).get("sport_event_context", {}).get("competition", {}).get("name", "N/A"),
            "match_data": match_summary,
            "match_status": match_status,
            "match_status_info": match_status_info,
            "formatted_data": formatted_data,
            "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        print(f"[ERROR] Error en fetch_match_live_data: {str(e)}")
        return {
            "success": False,
            "error": f"Error al obtener datos del partido: {str(e)}",
            "player_a": player_a,
            "player_b": player_b,
            "tournament": tournament or "N/A",
            "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


def format_match_data_structured(match_summary: Dict[str, Any]) -> str:
    """
    Formatea los datos del partido de Sportradar en un formato estructurado y legible.
    
    Args:
        match_summary (Dict[str, Any]): Datos del partido de Sportradar
    
    Returns:
        str: Datos formateados en texto estructurado para análisis
    """
    try:
        sport_event = match_summary.get("sport_event", {})
        sport_event_status = match_summary.get("sport_event_status", {})
        statistics = match_summary.get("statistics", {})
        
        # Extraer información básica
        competitors = sport_event.get("competitors", [])
        sport_event_context = sport_event.get("sport_event_context", {})
        venue = sport_event.get("venue", {})
        
        # Información del torneo
        competition = sport_event_context.get("competition", {})
        season = sport_event_context.get("season", {})
        
        # Estado del partido
        match_status = sport_event_status.get("status", "unknown")
        match_status_info = sport_event_status.get("match_status", "N/A")
        
        # Construir el reporte estructurado
        result = "# DATOS DEL PARTIDO (Sportradar API)\n\n"
        
        # Advertencia si el partido no está en vivo
        if match_status != "live":
            result += "⚠️ **ATENCIÓN: Este partido NO está actualmente EN VIVO**\n"
            result += f"**Estado actual:** {match_status} ({match_status_info})\n\n"
            if match_status == "not_started":
                result += "El partido aún no ha comenzado. Los datos mostrados son preliminares.\n\n"
            elif match_status in ["ended", "closed"]:
                result += "El partido ha finalizado. Los datos mostrados son el resultado final.\n\n"
            else:
                result += f"Estado: {match_status}\n\n"
        else:
            result += "✅ **PARTIDO EN VIVO**\n\n"
        
        result += "---\n\n"
        
        # 1. INFORMACIÓN BÁSICA
        result += "## 1. INFORMACIÓN BÁSICA DEL PARTIDO\n\n"
        
        if len(competitors) >= 2:
            home_player = competitors[0]
            away_player = competitors[1]
            
            result += f"**Jugador Local (Home):** {home_player.get('name', 'N/A')}\n"
            result += f"- País: {home_player.get('country', 'N/A')} ({home_player.get('country_code', 'N/A')})\n"
            result += f"- ID: {home_player.get('id', 'N/A')}\n\n"
            
            result += f"**Jugador Visitante (Away):** {away_player.get('name', 'N/A')}\n"
            result += f"- País: {away_player.get('country', 'N/A')} ({away_player.get('country_code', 'N/A')})\n"
            result += f"- ID: {away_player.get('id', 'N/A')}\n\n"
        
        result += f"**Torneo:** {competition.get('name', 'N/A')}\n"
        result += f"**Tipo:** {competition.get('type', 'N/A')} - {competition.get('gender', 'N/A')}\n"
        result += f"**Temporada:** {season.get('name', 'N/A')} ({season.get('year', 'N/A')})\n\n"
        
        result += f"**Fecha de inicio:** {sport_event.get('start_time', 'N/A')}\n"
        result += f"**Estado del partido:** {sport_event_status.get('status', 'N/A')}\n"
        result += f"**Match status:** {sport_event_status.get('match_status', 'N/A')}\n\n"
        
        result += f"**Ubicación:** {venue.get('name', 'N/A')}\n"
        result += f"**Ciudad:** {venue.get('city_name', 'N/A')}, {venue.get('country_name', 'N/A')}\n"
        result += f"**Timezone:** {venue.get('timezone', 'N/A')}\n\n"
        
        # 2. MARCADOR ACTUAL
        result += "## 2. MARCADOR ACTUAL\n\n"
        result += f"**Sets ganados:**\n"
        result += f"- Home: {sport_event_status.get('home_score', 0)} sets\n"
        result += f"- Away: {sport_event_status.get('away_score', 0)} sets\n\n"
        
        # Ganador (si existe)
        winner_id = sport_event_status.get('winner_id')
        if winner_id:
            result += f"**Ganador ID:** {winner_id}\n\n"
        
        # Desglose por sets
        period_scores = sport_event_status.get('period_scores', [])
        if period_scores:
            result += "**Desglose por Sets:**\n\n"
            for period in period_scores:
                set_num = period.get('number', 'N/A')
                home_score = period.get('home_score', 0)
                away_score = period.get('away_score', 0)
                result += f"- Set {set_num}: Home {home_score} - {away_score} Away"
                
                # Tie-breaks
                if 'home_tiebreak_score' in period or 'away_tiebreak_score' in period:
                    home_tb = period.get('home_tiebreak_score', 0)
                    away_tb = period.get('away_tiebreak_score', 0)
                    result += f" (Tiebreak: {home_tb}-{away_tb})"
                result += "\n"
            result += "\n"

        # Saque actual
        game_state = sport_event_status.get('game_state', {})
        if game_state:
            serving_side = game_state.get('serving')
            serving_label = serving_side.upper() if isinstance(serving_side, str) else 'N/A'
            serving_player = None

            if serving_side and len(competitors) >= 2:
                if serving_side == 'home':
                    serving_player = competitors[0].get('name', 'Jugador Home')
                elif serving_side == 'away':
                    serving_player = competitors[1].get('name', 'Jugador Away')

            if serving_player:
                result += f"**Saque actual:** {serving_player} ({serving_label})\n\n"
            elif serving_side:
                result += f"**Saque actual:** {serving_label}\n\n"
    
        # 3. ESTADÍSTICAS DETALLADAS
        result += "## 3. ESTADÍSTICAS DETALLADAS\n\n"
        
        totals = statistics.get('totals', {})
        competitors_stats = totals.get('competitors', [])
        
        if competitors_stats:
            for i, comp_stats in enumerate(competitors_stats):
                player_type = "HOME" if comp_stats.get('qualifier') == 'home' else "AWAY"
                player_name = comp_stats.get('name', 'N/A')
                stats = comp_stats.get('statistics', {})
                
                result += f"### Jugador {player_type}: {player_name}\n\n"
                
                result += "**Servicio:**\n"
                result += f"- Aces: {stats.get('aces', 0)}\n"
                result += f"- Dobles faltas: {stats.get('double_faults', 0)}\n"
                result += f"- Primer servicio exitoso: {stats.get('first_serve_successful', 0)}\n"
                result += f"- Puntos ganados con primer servicio: {stats.get('first_serve_points_won', 0)}\n"
                result += f"- Segundo servicio exitoso: {stats.get('second_serve_successful', 0)}\n"
                result += f"- Puntos ganados con segundo servicio: {stats.get('second_serve_points_won', 0)}\n"
                result += f"- Juegos de servicio ganados: {stats.get('service_games_won', 0)}\n"
                result += f"- Puntos de servicio ganados: {stats.get('service_points_won', 0)}\n"
                result += f"- Puntos de servicio perdidos: {stats.get('service_points_lost', 0)}\n\n"
                
                result += "**Break Points:**\n"
                result += f"- Break points ganados: {stats.get('breakpoints_won', 0)}\n"
                result += f"- Total de break points: {stats.get('total_breakpoints', 0)}\n"
                if stats.get('total_breakpoints', 0) > 0:
                    bp_pct = (stats.get('breakpoints_won', 0) / stats.get('total_breakpoints', 1)) * 100
                    result += f"- Efectividad: {bp_pct:.1f}%\n"
                result += "\n"
                
                result += "**Puntos y Juegos:**\n"
                result += f"- Total de puntos ganados: {stats.get('points_won', 0)}\n"
                result += f"- Juegos ganados: {stats.get('games_won', 0)}\n"
                result += f"- Tie-breaks ganados: {stats.get('tiebreaks_won', 0)}\n\n"
                
                result += "**Rachas:**\n"
                result += f"- Máximos puntos seguidos: {stats.get('max_points_in_a_row', 0)}\n"
                result += f"- Máximos juegos seguidos: {stats.get('max_games_in_a_row', 0)}\n\n"
                
                result += "---\n\n"
        else:
            result += "*No hay estadísticas detalladas disponibles para este partido*\n\n"
        
        # Información de cobertura
        coverage = sport_event.get('coverage', {})
        if coverage:
            result += "## 4. INFORMACIÓN DE COBERTURA\n\n"
            sport_event_props = coverage.get('sport_event_properties', {})
            result += f"- Enhanced stats: {sport_event_props.get('enhanced_stats', False)}\n"
            result += f"- Scores: {sport_event_props.get('scores', 'N/A')}\n"
            result += f"- Play by play: {sport_event_props.get('play_by_play', False)}\n\n"
        
        result += "---\n"
        result += "*Datos obtenidos de Sportradar Live Summaries API (actualización cada 1 segundo)*\n"
        
        return result
        
    except Exception as e:
        print(f"[ERROR] Error al formatear datos del partido: {str(e)}")
        # Fallback: devolver JSON crudo
        return f"""
## Error al Formatear Datos del Partido

**Error:** {str(e)}

### Datos Crudos (JSON)

```json
{json.dumps(match_summary, indent=2, ensure_ascii=False)}
```
"""


def format_match_live_report(match_data: Dict[str, Any]) -> str:
    """
    Formatea los datos del partido en vivo para presentación final.
    
    Args:
        match_data (Dict[str, Any]): Datos obtenidos de fetch_match_live_data()
    
    Returns:
        str: Reporte formateado del partido
    """
    if not match_data or match_data.get("success") == False:
        error_msg = match_data.get("error", "Error desconocido")
        note = match_data.get("note", "")
        
        result = f"## Error al Obtener Datos del Partido en Vivo\n\n"
        result += f"**Error:** {error_msg}\n\n"
        result += f"**Jugadores:** {match_data.get('player_a', 'N/A')} vs {match_data.get('player_b', 'N/A')}\n"
        result += f"**Torneo:** {match_data.get('tournament', 'N/A')}\n"
        result += f"**Fecha:** {match_data.get('fetched_at', 'N/A')}\n"
        
        if note:
            result += f"\n**Nota:** {note}\n"
        
        if match_data.get("total_live_matches"):
            result += f"\n**Partidos en vivo encontrados:** {match_data.get('total_live_matches')}\n"
        
        return result
    
    # Los datos ya vienen formateados de manera estructurada
    formatted_data = match_data.get("formatted_data", "No se pudieron formatear los datos")
    
    return formatted_data
