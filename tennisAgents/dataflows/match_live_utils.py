"""
Match Live Utilities - Herramientas para obtener datos en tiempo real de partidos de tenis
"""

from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, Any
from tennisAgents.dataflows.config import get_config

load_dotenv()


def fetch_match_live_data(player_a: str, player_b: str, tournament: str) -> Dict[str, Any]:
    """
    Obtiene datos en tiempo real del partido actual usando OpenAI con búsqueda web.
    
    Args:
        player_a (str): Nombre del primer jugador
        player_b (str): Nombre del segundo jugador
        tournament (str): Nombre del torneo
    
    Returns:
        Dict[str, Any]: Datos del partido en tiempo real
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
                    "text": f"""ANÁLISIS DE PARTIDO DE TENIS - FLASHCORE

OBJETIVO: Obtener información completa y actualizada del partido de tenis desde Flashcore.

INSTRUCCIONES ESPECÍFICAS:
1. PRIMERO intenta acceder a esta URL específica de Flashcore: https://www.flashscore.es/partido/tenis/alcaraz-garfia-carlos-UkhgIFEq/sinner-jannik-6HdC3z4H/resumen/estadisticas/0/?mid=4EAVYPi5
2. SEGUNDO, intenta acceder a esta URL específica de SofaScore: https://www.sofascore.com/tennis/match/carlos-alcaraz-jannik-sinner/vGHbsytkc#id:14494928,tab:statistics
3. Ambas URLs contienen el partido: Jannik Sinner vs Carlos Alcaraz del 07/09/2025
4. Si NO puedes acceder a esas URLs o no encuentras información, busca en otras fuentes deportivas confiables (ESPN, ATP, BBC Sport, etc.)
5. Analiza toda la información disponible en las fuentes que puedas acceder
6. Extrae todos los datos del partido disponibles
7. El objetivo es obtener información real y actualizada del partido

ENFOQUE DEL ANÁLISIS:
- PRIORIZA la URL específica de Flashcore
- SEGUNDO, consulta la URL específica de SofaScore
- Si no puedes acceder a ninguna de estas URLs, busca en otras fuentes deportivas confiables
- Analiza el partido Jannik Sinner vs Carlos Alcaraz del 07/09/2025
- Extrae todos los datos disponibles: resultado, estadísticas, resumen
- Confirma el estado del partido (finalizado, en vivo, programado)
- El objetivo es obtener información real y completa del partido

ESTRUCTURA DE DATOS A EXTRAER (BASADO EN EL FORMATO DE FLASHCORE):

**SECCIÓN SERVICIO (SERVICIO):**
- Aces: [número para cada jugador]
- Dobles faltas: [número para cada jugador] 
- Porcentaje 1er servicio: [% para cada jugador]
- Pts. ganados 1er serv.: [% (X/Y) para cada jugador]
- Pts. ganados 2º serv.: [% (X/Y) para cada jugador]
- Puntos break salvados: [% (X/Y) para cada jugador]
- Velocidad media del primer servicio: [km/h para cada jugador]
- Velocidad media del segundo servicio: [km/h para cada jugador]

**SECCIÓN RESTO (RETURN):**
- Pts. ganados 1ª devoluc.: [% (X/Y) para cada jugador]
- Pts. ganados 2ª devoluc.: [% (X/Y) para cada jugador]
- Puntos break convertidos: [% (X/Y) para cada jugador]

**SECCIÓN PUNTOS (PUNTOS):**
- Golpes Ganadores: [número para cada jugador]
- Errores No Forzados: [número para cada jugador]
- Puntos ganados en red: [% (X/Y) para cada jugador]
- Puntos ganados servicio: [% (X/Y) para cada jugador]
- Puntos ganados resto: [% (X/Y) para cada jugador]
- Total puntos ganados: [% (X/Y) para cada jugador]
- Últimos diez puntos: [número para cada jugador]
- Puntos de partido salvados: [número para cada jugador]

**SECCIÓN JUEGOS (JUEGOS):**
- Juegos ganados servicio: [% (X/Y) para cada jugador]
- Juegos ganados resto: [% (X/Y) para cada jugador]
- Total juegos ganados: [% (X/Y) para cada jugador]

INFORMACIÓN A REPORTAR:

1. **CONFIRMACIÓN DE ACCESO:**
   - ¿Pudiste acceder a la URL de Flashcore? (SÍ/NO)
   - ¿Pudiste acceder a la URL de SofaScore? (SÍ/NO)
   - Si NO pudiste acceder a ninguna de estas URLs, ¿qué otras fuentes consultaste? (ESPN, ATP, BBC Sport, etc.)
   - URL(es) consultada(s)
   - Estado de acceso a cada fuente

2. **INFORMACIÓN DEL PARTIDO:**
   - ¿Encontraste el partido Jannik Sinner vs Carlos Alcaraz del 07/09/2025? (SÍ/NO)
   - Estado del partido: "FINALIZADO", "EN VIVO", "PROGRAMADO"
   - Fecha y hora del partido
   - Resultado final por sets 

3. **ESTADÍSTICAS COMPLETAS (OBLIGATORIO - SOLO DATOS REALES DE LA PÁGINA):**

**IMPORTANTE: SOLO reporta datos que veas REALMENTE en la página. Si no ves un dato, escribe "NO DISPONIBLE".**

**SERVICIO:**
- Aces: Carlos Alcaraz: [X - SOLO si lo ves en la página], Jannik Sinner: [Y - SOLO si lo ves en la página]
- Dobles faltas: Carlos Alcaraz: [X - SOLO si lo ves en la página], Jannik Sinner: [Y - SOLO si lo ves en la página]
- Porcentaje 1er servicio: Carlos Alcaraz: [X% - SOLO si lo ves en la página], Jannik Sinner: [Y% - SOLO si lo ves en la página]
- Pts. ganados 1er serv.: Carlos Alcaraz: [X% (A/B) - SOLO si lo ves en la página], Jannik Sinner: [Y% (C/D) - SOLO si lo ves en la página]
- Pts. ganados 2º serv.: Carlos Alcaraz: [X% (A/B) - SOLO si lo ves en la página], Jannik Sinner: [Y% (C/D) - SOLO si lo ves en la página]
- Puntos break salvados: Carlos Alcaraz: [X% (A/B) - SOLO si lo ves en la página], Jannik Sinner: [Y% (C/D) - SOLO si lo ves en la página]
- Velocidad media 1er serv.: Carlos Alcaraz: [X km/h - SOLO si lo ves en la página], Jannik Sinner: [Y km/h - SOLO si lo ves en la página]
- Velocidad media 2º serv.: Carlos Alcaraz: [X km/h - SOLO si lo ves en la página], Jannik Sinner: [Y km/h - SOLO si lo ves en la página]

**RESTO:**
- Pts. ganados 1ª devoluc.: Carlos Alcaraz: [X% (A/B) - SOLO si lo ves en la página], Jannik Sinner: [Y% (C/D) - SOLO si lo ves en la página]
- Pts. ganados 2ª devoluc.: Carlos Alcaraz: [X% (A/B) - SOLO si lo ves en la página], Jannik Sinner: [Y% (C/D) - SOLO si lo ves en la página]
- Puntos break convertidos: Carlos Alcaraz: [X% (A/B) - SOLO si lo ves en la página], Jannik Sinner: [Y% (C/D) - SOLO si lo ves en la página]

**PUNTOS:**
- Golpes Ganadores: Carlos Alcaraz: [X - SOLO si lo ves en la página], Jannik Sinner: [Y - SOLO si lo ves en la página]
- Errores No Forzados: Carlos Alcaraz: [X - SOLO si lo ves en la página], Jannik Sinner: [Y - SOLO si lo ves en la página]
- Puntos ganados en red: Carlos Alcaraz: [X% (A/B) - SOLO si lo ves en la página], Jannik Sinner: [Y% (C/D) - SOLO si lo ves en la página]
- Puntos ganados servicio: Carlos Alcaraz: [X% (A/B) - SOLO si lo ves en la página], Jannik Sinner: [Y% (C/D) - SOLO si lo ves en la página]
- Puntos ganados resto: Carlos Alcaraz: [X% (A/B) - SOLO si lo ves en la página], Jannik Sinner: [Y% (C/D) - SOLO si lo ves en la página]
- Total puntos ganados: Carlos Alcaraz: [X% (A/B) - SOLO si lo ves en la página], Jannik Sinner: [Y% (C/D) - SOLO si lo ves en la página]
- Últimos diez puntos: Carlos Alcaraz: [X - SOLO si lo ves en la página], Jannik Sinner: [Y - SOLO si lo ves en la página]
- Puntos de partido salvados: Carlos Alcaraz: [X - SOLO si lo ves en la página], Jannik Sinner: [Y - SOLO si lo ves en la página]

**JUEGOS:**
- Juegos ganados servicio: Carlos Alcaraz: [X% (A/B) - SOLO si lo ves en la página], Jannik Sinner: [Y% (C/D) - SOLO si lo ves en la página]
- Juegos ganados resto: Carlos Alcaraz: [X% (A/B) - SOLO si lo ves en la página], Jannik Sinner: [Y% (C/D) - SOLO si lo ves en la página]
- Total juegos ganados: Carlos Alcaraz: [X% (A/B) - SOLO si lo ves en la página], Jannik Sinner: [Y% (C/D) - SOLO si lo ves en la página]

4. **EVIDENCIA DE ACCESO:**
   - Descripción detallada de lo encontrado en la página
   - Confirmación de que los datos son reales de Flashcore
   - Cualquier error o problema de acceso

5. **VALIDACIÓN DE DATOS:**
   - Confirma que cada estadística reportada fue vista REALMENTE en la página
   - Si no pudiste acceder a la página, escribe "ERROR DE ACCESO - NO SE PUDO OBTENER DATOS"
   - Si la página no carga o hay errores, escribe "PÁGINA NO DISPONIBLE - NO SE PUDO OBTENER DATOS"
   - Si no ves estadísticas específicas, escribe "NO DISPONIBLE" para cada dato faltante
   - NO inventes, estimes o generes datos ficticios

INSTRUCCIONES CRÍTICAS - SOLO DATOS REALES:
- NUNCA inventes o generes estadísticas ficticias
- SOLO reporta datos que veas REALMENTE en las fuentes consultadas
- Si no puedes acceder a Flashcore o SofaScore, busca en otras fuentes deportivas confiables
- Si no puedes acceder a ninguna fuente o no ves datos, escribe "NO DISPONIBLE" o "ERROR DE ACCESO"
- En Flashcore, busca específicamente las secciones "SERVICIO", "RESTO", "PUNTOS" y "JUEGOS"
- En SofaScore, busca la pestaña "Statistics" y las estadísticas detalladas del partido
- En otras fuentes, busca estadísticas similares (aces, dobles faltas, porcentajes, etc.)
- Extrae ÚNICAMENTE los valores numéricos que aparezcan REALMENTE en las fuentes
- Los valores aparecen como números enteros o porcentajes con fracciones (X/Y)
- Si no encuentras un dato específico, escribe "NO DISPONIBLE" - NO lo inventes
- Confirma qué fuentes pudiste consultar y cuáles no
- Los datos deben ser reales y actualizados del partido
- Si ves estadísticas en las fuentes, extrae esos números exactos
- Si no puedes acceder a las fuentes o hay errores, reporta el problema específico
- NO generes números aleatorios o estimaciones
- NO uses datos de partidos anteriores o de tu conocimiento
- SOLO datos extraídos directamente de las fuentes web consultadas
- SIEMPRE indica claramente qué información NO pudiste encontrar"""
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
                "search_context_size": "high",
            }
            ],
            temperature=0.1,
            max_output_tokens=4096,
            top_p=0.9,
            store=True,
        )
        match_info = response.output[1].content[0].text
        print(f"[DEBUG] Raw match info response: {match_info}")
        
        # Extraer URLs de las fuentes si están presentes
        sources = []
        if "FUENTES:" in match_info:
            sources_section = match_info.split("FUENTES:")[1].strip()
            # Buscar URLs en el texto
            import re
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            urls = re.findall(url_pattern, sources_section)
            sources.extend(urls)
        
        # Construir el resultado estructurado
        result = {
            "success": True,
            "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "tournament": tournament,
            "player_a": player_a,
            "player_b": player_b,
            "match_information": match_info,
            "sources": sources,
            "source": "OpenAI Web Search",
            "note": "Información obtenida en tiempo real mediante búsqueda web."
        }

        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error al obtener datos del partido: {str(e)}",
            "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "tournament": tournament,
            "player_a": player_a,
            "player_b": player_b
        }


def format_match_live_report(match_data: Dict[str, Any]) -> str:
    """
    Formatea los datos del partido en vivo en un reporte legible.
    
    Args:
        match_data (Dict[str, Any]): Datos del partido obtenidos de fetch_match_live_data
    
    Returns:
        str: Reporte formateado del partido en vivo
    """
    
    if not match_data or match_data.get("success") == False:
        error_msg = match_data.get("error", "Error desconocido al obtener datos del partido en vivo.")
        return f"Error al obtener datos del partido en vivo: {error_msg}"
    
    player_a = match_data["player_a"]
    player_b = match_data["player_b"]
    tournament = match_data["tournament"]
    
    result = f"## Información en Tiempo Real - {tournament}\n\n"
    result += f"**{player_a} vs {player_b}**\n\n"
    
    # Información del partido obtenida por OpenAI
    result += f"### Información del Partido\n"
    result += f"{match_data['match_information']}\n\n"
    
    # Metadatos
    result += f"### Metadatos\n"
    result += f"- **Última Actualización:** {match_data['fetched_at']}\n"
    result += f"- **Fuente:** {match_data['source']}\n"
    result += f"- **Nota:** {match_data['note']}\n"
    
    # Fuentes consultadas
    if match_data.get('sources'):
        result += f"\n### Fuentes Consultadas\n"
        for i, source_url in enumerate(match_data['sources'], 1):
            result += f"{i}. {source_url}\n"
    else:
        result += f"\n### Fuentes Consultadas\n"
        result += f"- No se pudieron extraer URLs de fuentes específicas\n"
    
    return result


def mock_match_live_data(player_a: str, player_b: str, tournament: str) -> Dict[str, Any]:
    """
    Genera datos ficticios de partido en vivo para un partido específico.
    
    Reglas del tenis para sets:
    - Un set termina cuando un jugador alcanza 6 juegos con diferencia de 2
    - Posibles resultados: 6-0, 6-1, 6-2, 6-3, 6-4, 7-5, 7-6
    - 7-6 solo es posible en tie-break
    - 7-5 solo es posible si el oponente tiene 5 juegos
    
    Args:
        player_a (str): Nombre del primer jugador
        player_b (str): Nombre del segundo jugador
        tournament (str): Nombre del torneo
    
    Returns:
        Dict[str, Any]: Datos ficticios del partido en vivo
    """
    
    import random
    from datetime import datetime, timedelta
    
    # Generar estado del partido aleatorio
    match_states = ["en curso", "finalizado", "próximo"]
    current_state = random.choice(match_states)
    
    # Generar sets aleatorios
    if current_state == "en curso":
        # Partido en curso - generar sets parciales
        sets_completed = random.randint(1, 4)
        current_set = random.randint(1, 5)
        current_game = random.randint(1, 6)
        
        sets = []
        for i in range(sets_completed):
            if i == current_set - 1:
                # Set actual en curso
                sets.append(f"{current_game}-{random.randint(0, 5)} en curso")
            else:
                # Sets completados - deben seguir las reglas del tenis
                # Un set termina en 6-0, 6-1, 6-2, 6-3, 6-4, 7-5, o 7-6
                set_winner = random.choice([player_a, player_b])
                if set_winner == player_a:
                    # Player A gana el set
                    if random.random() < 0.3:  # 30% probabilidad de 7-6
                        sets.append("7-6")
                    elif random.random() < 0.2:  # 20% probabilidad de 7-5
                        sets.append("7-5")
                    else:  # 50% probabilidad de 6-X
                        opponent_score = random.randint(0, 4)
                        sets.append(f"6-{opponent_score}")
                else:
                    # Player B gana el set
                    if random.random() < 0.3:  # 30% probabilidad de 7-6
                        sets.append("6-7")
                    elif random.random() < 0.2:  # 20% probabilidad de 7-5
                        sets.append("5-7")
                    else:  # 50% probabilidad de 6-X
                        opponent_score = random.randint(0, 4)
                        sets.append(f"{opponent_score}-6")
        
        # Agregar set actual si no está en la lista
        if current_set > sets_completed:
            sets.append(f"{current_game}-{random.randint(0, 5)} en curso")
            
    elif current_state == "finalizado":
        # Partido finalizado - generar resultado completo
        sets = []
        player_a_sets = 0
        player_b_sets = 0
        
        # Generar 3-5 sets
        total_sets = random.choice([3, 5])
        for i in range(total_sets):
            if player_a_sets >= 3 or player_b_sets >= 3:
                break
                
            # Generar set siguiendo las reglas del tenis
            set_winner = random.choice([player_a, player_b])
            if set_winner == player_a:
                # Player A gana el set
                if random.random() < 0.3:  # 30% probabilidad de 7-6
                    sets.append("7-6")
                elif random.random() < 0.2:  # 20% probabilidad de 7-5
                    sets.append("7-5")
                else:  # 50% probabilidad de 6-X
                    opponent_score = random.randint(0, 4)
                    sets.append(f"6-{opponent_score}")
                player_a_sets += 1
            else:
                # Player B gana el set
                if random.random() < 0.3:  # 30% probabilidad de 7-6
                    sets.append("6-7")
                elif random.random() < 0.2:  # 20% probabilidad de 7-5
                    sets.append("5-7")
                else:  # 50% probabilidad de 6-X
                    opponent_score = random.randint(0, 4)
                    sets.append(f"{opponent_score}-6")
                player_b_sets += 1
                
    else:
        # Partido próximo
        sets = ["Próximo"]
    
    # Generar estadísticas aleatorias
    aces_player_a = random.randint(2, 15)
    aces_player_b = random.randint(2, 15)
    double_faults_player_a = random.randint(0, 8)
    double_faults_player_b = random.randint(0, 8)
    
    first_serve_percentage_a = random.randint(55, 85)
    first_serve_percentage_b = random.randint(55, 85)
    
    first_serve_points_won_a = random.randint(65, 90)
    first_serve_points_won_b = random.randint(65, 90)
    
    second_serve_points_won_a = random.randint(45, 75)
    second_serve_points_won_b = random.randint(45, 75)
    
    break_points_converted_a = random.randint(1, 8)
    break_points_total_a = random.randint(3, 12)
    break_points_converted_b = random.randint(1, 8)
    break_points_total_b = random.randint(3, 12)
    
    total_points_won_a = random.randint(80, 150)
    total_points_won_b = random.randint(80, 150)
    
    service_games_won_a = random.randint(8, 15)
    service_games_total_a = random.randint(12, 20)
    service_games_won_b = random.randint(8, 15)
    service_games_total_b = random.randint(12, 20)
    
    # Generar momentum y análisis táctico
    momentum_indicators = [
        f"{player_a} está dominando con su servicio",
        f"{player_b} está ganando puntos clave en momentos importantes",
        f"Ambos jugadores están muy equilibrados",
        f"{player_a} está aprovechando los errores de {player_b}",
        f"{player_b} está defendiendo muy bien",
        f"{player_a} está jugando de manera agresiva",
        f"{player_b} está controlando el ritmo del partido"
    ]
    
    tactical_analysis = [
        f"{player_a} está usando su revés de slice para variar el juego",
        f"{player_b} está atacando la red en momentos clave",
        f"{player_a} está sacando muy bien en momentos de presión",
        f"{player_b} está defendiendo muy bien desde el fondo",
        f"{player_a} está usando dropshots para sorprender",
        f"{player_b} está jugando con mucha consistencia"
    ]
    
    # Generar información del torneo
    tournament_phases = [
        "Primera Ronda", "Segunda Ronda", "Tercera Ronda", "Cuartos de Final",
        "Semifinal", "Final", "Qualifying Round", "Round Robin"
    ]
    
    tournament_phase = random.choice(tournament_phases)
    
    # Generar ubicación
    locations = [
        "Melbourne, Australia", "Paris, Francia", "Londres, Reino Unido", 
        "Nueva York, Estados Unidos", "Madrid, España", "Roma, Italia",
        "Miami, Estados Unidos", "Toronto, Canadá", "Shanghai, China"
    ]
    
    location = random.choice(locations)
    
    # Generar fecha
    match_date = datetime.now() - timedelta(hours=random.randint(0, 48))
    
    # Construir el resultado estructurado
    result = {
        "success": True,
        "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "tournament": tournament,
        "tournament_phase": tournament_phase,
        "player_a": player_a,
        "player_b": player_b,
        "match_state": current_state,
        "location": location,
        "match_date": match_date.strftime('%Y-%m-%d %H:%M:%S'),
        "sets": sets,
        "statistics": {
            "aces": {
                player_a: aces_player_a,
                player_b: aces_player_b
            },
            "double_faults": {
                player_a: double_faults_player_a,
                player_b: double_faults_player_b
            },
            "first_serve_percentage": {
                player_a: f"{first_serve_percentage_a}%",
                player_b: f"{first_serve_percentage_b}%"
            },
            "first_serve_points_won": {
                player_a: f"{first_serve_points_won_a}%",
                player_b: f"{first_serve_points_won_b}%"
            },
            "second_serve_points_won": {
                player_a: f"{second_serve_points_won_a}%",
                player_b: f"{second_serve_points_won_b}%"
            },
            "break_points": {
                player_a: f"{break_points_converted_a}/{break_points_total_a}",
                player_b: f"{break_points_converted_b}/{break_points_total_b}"
            },
            "total_points_won": {
                player_a: total_points_won_a,
                player_b: total_points_won_b
            },
            "service_games": {
                player_a: f"{service_games_won_a}/{service_games_total_a}",
                player_b: f"{service_games_won_b}/{service_games_total_b}"
            }
        },
        "momentum": random.choice(momentum_indicators),
        "tactical_analysis": random.choice(tactical_analysis),
        "source": "Datos Ficticios Generados",
        "note": "Información generada para propósitos de demostración y testing."
    }
    
    return result


def format_mock_match_live_report(match_data: Dict[str, Any]) -> str:
    """
    Formatea los datos ficticios del partido en vivo en un reporte legible.
    
    Args:
        match_data (Dict[str, Any]): Datos ficticios del partido obtenidos de mock_match_live_data
    
    Returns:
        str: Reporte formateado del partido en vivo con datos ficticios
    """
    
    if not match_data or match_data.get("success") == False:
        error_msg = match_data.get("error", "Error desconocido al generar datos ficticios del partido.")
        return f"Error al generar datos ficticios del partido: {error_msg}"
    
    player_a = match_data["player_a"]
    player_b = match_data["player_b"]
    tournament = match_data["tournament"]
    tournament_phase = match_data.get("tournament_phase", "N/A")
    match_state = match_data.get("match_state", "N/A")
    location = match_data.get("location", "N/A")
    match_date = match_data.get("match_date", "N/A")
    sets = match_data.get("sets", [])
    statistics = match_data.get("statistics", {})
    momentum = match_data.get("momentum", "N/A")
    tactical_analysis = match_data.get("tactical_analysis", "N/A")
    
    result = f"## Información en Tiempo Real (Ficticia) - {tournament}\n\n"
    result += f"**{player_a} vs {player_b}**\n\n"
    
    # Información general
    result += f"### Información General\n"
    result += f"- **Torneo:** {tournament} - {tournament_phase}\n"
    result += f"- **Ubicación:** {location}\n"
    result += f"- **Fecha del Partido:** {match_date}\n"
    result += f"- **Estado:** {match_state.capitalize()}\n\n"
    
    # Marcador en vivo
    result += f"### Marcador en Vivo\n"
    if sets and sets != ["Próximo"]:
        for i, set_score in enumerate(sets, 1):
            result += f"- **Set {i}:** {set_score}\n"
    else:
        result += f"- **Estado:** {sets[0] if sets else 'N/A'}\n"
    result += "\n"
    
    # Estadísticas del partido
    result += f"### Estadísticas del Partido\n"
    
    if "aces" in statistics:
        result += f"**Aces:**\n"
        result += f"- {player_a}: {statistics['aces'].get(player_a, 'N/A')}\n"
        result += f"- {player_b}: {statistics['aces'].get(player_b, 'N/A')}\n\n"
    
    if "double_faults" in statistics:
        result += f"**Dobles Faltas:**\n"
        result += f"- {player_a}: {statistics['double_faults'].get(player_a, 'N/A')}\n"
        result += f"- {player_b}: {statistics['double_faults'].get(player_b, 'N/A')}\n\n"
    
    if "first_serve_percentage" in statistics:
        result += f"**Porcentaje de Primer Servicio:**\n"
        result += f"- {player_a}: {statistics['first_serve_percentage'].get(player_a, 'N/A')}\n"
        result += f"- {player_b}: {statistics['first_serve_percentage'].get(player_b, 'N/A')}\n\n"
    
    if "first_serve_points_won" in statistics:
        result += f"**Puntos Ganados con Primer Servicio:**\n"
        result += f"- {player_a}: {statistics['first_serve_points_won'].get(player_a, 'N/A')}\n"
        result += f"- {player_b}: {statistics['first_serve_points_won'].get(player_b, 'N/A')}\n\n"
    
    if "second_serve_points_won" in statistics:
        result += f"**Puntos Ganados con Segundo Servicio:**\n"
        result += f"- {player_a}: {statistics['second_serve_points_won'].get(player_a, 'N/A')}\n"
        result += f"- {player_b}: {statistics['second_serve_points_won'].get(player_b, 'N/A')}\n\n"
    
    if "break_points" in statistics:
        result += f"**Break Points:**\n"
        result += f"- {player_a}: {statistics['break_points'].get(player_a, 'N/A')}\n"
        result += f"- {player_b}: {statistics['break_points'].get(player_b, 'N/A')}\n\n"
    
    if "total_points_won" in statistics:
        result += f"**Total de Puntos Ganados:**\n"
        result += f"- {player_a}: {statistics['total_points_won'].get(player_a, 'N/A')}\n"
        result += f"- {player_b}: {statistics['total_points_won'].get(player_b, 'N/A')}\n\n"
    
    if "service_games" in statistics:
        result += f"**Juegos de Servicio:**\n"
        result += f"- {player_a}: {statistics['service_games'].get(player_a, 'N/A')}\n"
        result += f"- {player_b}: {statistics['service_games'].get(player_b, 'N/A')}\n\n"
    
    # Análisis táctico y momentum
    result += f"### Análisis del Partido\n"
    result += f"**Momentum Actual:** {momentum}\n\n"
    result += f"**Análisis Táctico:** {tactical_analysis}\n\n"
    
    # Metadatos
    result += f"### Metadatos\n"
    result += f"- **Última Actualización:** {match_data['fetched_at']}\n"
    result += f"- **Fuente:** {match_data['source']}\n"
    result += f"- **Nota:** {match_data['note']}\n"
    
    return result
