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


def player_name_matches(api_name: str, search_name: str) -> bool:
    """
    Verifica si un nombre de jugador de la API coincide con el nombre buscado.
    
    La API de Sportradar devuelve nombres en formato "Apellido, Nombre" o variaciones.
    Esta función maneja diferentes formatos y normaliza los nombres para comparación.
    
    Args:
        api_name (str): Nombre del jugador como viene de la API (ej: "Djokovic, Novak")
        search_name (str): Nombre buscado (ej: "Djokovic" o "Novak Djokovic")
    
    Returns:
        bool: True si los nombres coinciden
    """
    # Normalizar ambos nombres
    api_normalized = normalize_name(api_name)
    search_normalized = normalize_name(search_name)
    
    # Si el nombre buscado está en el nombre de la API, es una coincidencia
    if search_normalized in api_normalized:
        return True
    
    # Si el nombre de la API tiene formato "Apellido, Nombre", intentar invertirlo
    if ',' in api_name:
        parts = [normalize_name(p.strip()) for p in api_name.split(',')]
        # Probar "Nombre Apellido"
        reversed_name = ' '.join(reversed(parts))
        if search_normalized in reversed_name or reversed_name in search_normalized:
            return True
    
    # Probar si alguna palabra del nombre buscado está en el nombre de la API
    search_words = search_normalized.split()
    for word in search_words:
        if len(word) >= 3 and word in api_normalized:  # Solo palabras de 3+ caracteres
            return True
    
    return False


def fetch_live_summaries() -> Dict[str, Any]:
    """
    Obtiene todos los resúmenes de partidos en vivo desde la API de Sportradar.
    
    Returns:
        Dict[str, Any]: Diccionario con:
            - success (bool): Si la operación fue exitosa
            - data (Dict): Datos completos de la API
            - total_matches (int): Número total de partidos en vivo
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
        
        print(f"[SUCCESS] Se obtuvieron {len(summaries)} partidos en vivo")
        
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


def tournament_name_matches(api_tournament: str, search_tournament: str) -> bool:
    """
    Verifica si un nombre de torneo de la API coincide con el nombre buscado.
    
    Maneja:
    - Variaciones de idioma (Masculino/Men, Femenino/Women)
    - Nombres parciales (Roanne vs ATP Challenger Roanne, France)
    - Diferentes formatos
    
    Args:
        api_tournament (str): Nombre del torneo como viene de la API
        search_tournament (str): Nombre del torneo buscado
    
    Returns:
        bool: True si los nombres coinciden
    """
    # Normalizar ambos nombres
    api_normalized = normalize_name(api_tournament)
    search_normalized = normalize_name(search_tournament)
    
    # Mapeo de traducciones comunes
    translations = {
        'masculino': 'men',
        'femenino': 'women',
        'mens': 'men',
        'womens': 'women',
        'singles': 'individual',
        'doubles': 'dobles',
    }
    
    # Aplicar traducciones al nombre buscado
    for spanish, english in translations.items():
        search_normalized = search_normalized.replace(spanish, english)
        api_normalized = api_normalized.replace(spanish, english)
    
    # Estrategia 1: El nombre buscado está contenido en el nombre de la API
    if search_normalized in api_normalized:
        return True
    
    # Estrategia 2: Extraer palabras clave significativas (3+ caracteres) y verificar que la mayoría coincidan
    search_words = [w for w in search_normalized.split() if len(w) >= 3]
    api_words = set([w for w in api_normalized.split() if len(w) >= 3])
    
    # Si al menos el 60% de las palabras clave están presentes, considerar match
    if search_words:
        matches = sum(1 for word in search_words if word in api_words)
        match_ratio = matches / len(search_words)
        if match_ratio >= 0.6:
            return True
    
    return False


def find_match_in_summaries(
    summaries_data: Dict[str, Any],
    player_a: str,
    player_b: str,
    tournament: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Busca un partido específico dentro de los resúmenes de partidos en vivo.
    
    Args:
        summaries_data (Dict[str, Any]): Datos obtenidos de fetch_live_summaries()
        player_a (str): Nombre del primer jugador
        player_b (str): Nombre del segundo jugador
        tournament (Optional[str]): Nombre del torneo (opcional para filtrar)
    
    Returns:
        Optional[Dict[str, Any]]: Datos del partido encontrado o None si no se encuentra
    """
    if not summaries_data.get("success"):
        return None
    
    summaries = summaries_data.get("data", {}).get("summaries", [])
    
    print(f"[INFO] Buscando partido entre '{player_a}' y '{player_b}'")
    if tournament:
        print(f"[INFO] Filtrando por torneo: '{tournament}'")
    
    for summary in summaries:
        sport_event = summary.get("sport_event", {})
        competitors = sport_event.get("competitors", [])
        
        # Verificar si tenemos exactamente 2 competidores
        if len(competitors) != 2:
            continue
        
        competitor_names = [comp.get("name", "") for comp in competitors]
        
        # Verificar si ambos jugadores están en el partido
        player_a_found = any(player_name_matches(name, player_a) for name in competitor_names)
        player_b_found = any(player_name_matches(name, player_b) for name in competitor_names)
        
        if player_a_found and player_b_found:
            # Si se especificó torneo, verificar que coincida
            if tournament:
                competition_name = sport_event.get("sport_event_context", {}).get("competition", {}).get("name", "")
                
                if not tournament_name_matches(competition_name, tournament):
                    print(f"[INFO] Partido encontrado pero torneo no coincide: '{competition_name}' vs '{tournament}'")
                    continue
            
            print(f"[SUCCESS] Partido encontrado: {competitor_names[0]} vs {competitor_names[1]}")
            return summary
    
    print(f"[WARNING] No se encontró el partido entre '{player_a}' y '{player_b}'")
    return None


def fetch_match_live_data(player_a: str, player_b: str, tournament: Optional[str] = None) -> Dict[str, Any]:
    """
    Obtiene datos en tiempo real de un partido específico usando Sportradar API.
    
    Flujo:
    1. Obtiene todos los partidos en vivo desde Sportradar
    2. Busca el partido específico entre los dos jugadores
    3. Extrae y estructura la información relevante del partido
    
    Args:
        player_a (str): Nombre del primer jugador
        player_b (str): Nombre del segundo jugador
        tournament (Optional[str]): Nombre del torneo (opcional)
    
    Returns:
        Dict[str, Any]: Diccionario con:
            - success (bool): Si la operación fue exitosa
            - player_a (str): Nombre del jugador A
            - player_b (str): Nombre del jugador B
            - tournament (str): Nombre del torneo
            - match_data (Dict): Datos estructurados del partido
            - formatted_data (str): Datos formateados en texto para el agente
            - fetched_at (str): Timestamp de la consulta
            - error (str): Mensaje de error si falló
    """
    try:
        print(f"\n[INFO] Iniciando búsqueda de partido en vivo: {player_a} vs {player_b}")
        if tournament:
            print(f"[INFO] Torneo: {tournament}")
        
        # 1. Obtener todos los partidos en vivo
        summaries_data = fetch_live_summaries()
        
        if not summaries_data.get("success"):
            return {
                "success": False,
                "error": summaries_data.get("error", "Error al obtener partidos en vivo"),
                "player_a": player_a,
                "player_b": player_b,
                "tournament": tournament or "N/A",
                "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        # 2. Buscar el partido específico
        match_summary = find_match_in_summaries(summaries_data, player_a, player_b, tournament)
        
        if not match_summary:
            return {
                "success": False,
                "error": f"No se encontró el partido entre {player_a} y {player_b} en los partidos en vivo",
                "player_a": player_a,
                "player_b": player_b,
                "tournament": tournament or "N/A",
                "total_live_matches": summaries_data.get("total_matches", 0),
                "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "note": "Verifica que el partido esté en curso y que los nombres de los jugadores sean correctos"
            }
        
        # 3. Formatear los datos de manera estructurada
        formatted_data = format_match_data_structured(match_summary)
        
        return {
            "success": True,
            "player_a": player_a,
            "player_b": player_b,
            "tournament": match_summary.get("sport_event", {}).get("sport_event_context", {}).get("competition", {}).get("name", "N/A"),
            "match_data": match_summary,
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
        
        # Construir el reporte estructurado
        result = "# DATOS DEL PARTIDO EN VIVO (Sportradar API)\n\n"
        
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
