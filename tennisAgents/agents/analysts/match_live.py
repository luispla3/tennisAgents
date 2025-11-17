from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies

def create_match_live_analyst(llm, toolkit):
    def match_live_analyst_node(state):
        """
        Analista de Partidos en Vivo - Obtiene información en tiempo real usando Sportradar API con OpenAI.
        
        Flujo de trabajo automático:
        1. Recibe los nombres de los jugadores y torneo del estado
        2. Usa la herramienta get_match_live_data que internamente:
           a) Obtiene todos los partidos en vivo desde Sportradar Live Summaries API
           b) Busca el partido específico entre los dos jugadores (con búsqueda flexible)
           c) Extrae la información relevante del partido (marcador, estadísticas, etc.)
        3. Retorna el reporte con marcador, estadísticas y análisis del momentum
        
        """
        match_date = state[STATE.match_date]
        player_a = state[STATE.player_of_interest]
        player_b = state[STATE.opponent]
        tournament = state[STATE.tournament]
        surface = state.get(STATE.surface, "")
        
        # Herramienta para obtener datos reales del partido en vivo desde Sportradar API
        tools = [toolkit.get_match_live_data]

        # Obtener la anatomía del prompt para analista de partidos en vivo
        anatomy = TennisAnalystAnatomies.match_live_analyst()

        # Información de herramientas
        tools_info = (
            "• get_match_live_data(player_a, player_b, tournament) - Obtiene información en tiempo real del partido desde Sportradar API, "
            "incluyendo marcador actual, estadísticas detalladas y análisis del partido"
        )

        # Contexto adicional específico para la obtención de datos en vivo
        additional_context = (
            "OBTENCIÓN Y ANÁLISIS DE DATOS EN TIEMPO REAL CON SPORTRADAR API:\n\n"
            f"1. PRIMER PASO - OBTENER DATOS:\n"
            f"   DEBES usar UNA ÚNICA VEZ la herramienta 'get_match_live_data' con estos parámetros:\n"
            f"   - player_a: '{player_a}'\n"
            f"   - player_b: '{player_b}'\n"
            f"   - tournament: '{tournament}'\n\n"
            "2. QUÉ HACE LA HERRAMIENTA:\n"
            "   a) Obtiene todos los partidos en vivo desde Sportradar Live Summaries API\n"
            "   b) Busca el partido específico entre los dos jugadores (búsqueda flexible)\n"
            "   c) Extrae y formatea la información del partido en formato estructurado:\n"
            "      • Información básica (jugadores, torneo, fecha, estado)\n"
            "      • Marcador actual (sets ganados, desglose por sets, tie-breaks)\n"
            "      • Estadísticas detalladas por jugador (servicio, break points, puntos, rachas)\n\n"
            "3. NO PROCEDAS SIN LLAMAR A LA HERRAMIENTA PRIMERO\n\n"
            "4. SEGUNDO PASO - ANALIZAR LOS DATOS:\n"
            "   Una vez que la herramienta te devuelva los datos formateados, TU TAREA es:\n"
            "   a) Leer y comprender todos los datos estructurados\n"
            "   b) Analizar el marcador y las estadísticas\n"
            "   c) Generar un reporte completo con tu análisis experto\n\n"
            "5. ESTRUCTURA DEL REPORTE QUE DEBES GENERAR:\n\n"
            "## 1. RESUMEN DEL PARTIDO\n"
            "   - Jugadores (con nombres completos de los datos)\n"
            "   - Torneo y ubicación\n"
            "   - Estado del partido (live/ended/closed)\n"
            "   - Marcador de sets actual (X-X)\n\n"
            "## 2. MARCADOR DETALLADO\n"
            "   - Desglose por sets con juegos de cada set\n"
            "   - Tie-breaks si los hubo\n"
            "   - Indica explícitamente quién está sacando actualmente mapeando el campo 'serving' del objeto game_state (home/away) al nombre del jugador correspondiente\n"
            "   - Identificar claramente quién va ganando o quién ganó\n\n"
            "## 3. ESTADÍSTICAS COMPLETAS EN TIEMPO REAL\n"
            "   DEBES incluir TODAS las estadísticas disponibles en formato de tabla comparativa.\n"
            "   Crea UNA TABLA COMPLETA con TODAS estas estadísticas para ambos jugadores:\n"
            "   \n"
            "   | Estadística | Jugador 1 | Jugador 2 |\n"
            "   |------------|-----------|----------|\n"
            "   | **SERVICIO** | | |\n"
            "   | Aces | [número] | [número] |\n"
            "   | Dobles faltas | [número] | [número] |\n"
            "   | Primer servicio exitoso | [número] | [número] |\n"
            "   | Puntos ganados 1er servicio | [número] | [número] |\n"
            "   | % efectividad 1er servicio | [calcular %] | [calcular %] |\n"
            "   | Segundo servicio exitoso | [número] | [número] |\n"
            "   | Puntos ganados 2do servicio | [número] | [número] |\n"
            "   | % efectividad 2do servicio | [calcular %] | [calcular %] |\n"
            "   | Juegos de servicio ganados | [número] | [número] |\n"
            "   | Puntos de servicio ganados | [número] | [número] |\n"
            "   | Puntos de servicio perdidos | [número] | [número] |\n"
            "   | **BREAK POINTS** | | |\n"
            "   | Break points convertidos | [número] | [número] |\n"
            "   | Total break points | [número] | [número] |\n"
            "   | % efectividad break points | [calcular %] | [calcular %] |\n"
            "   | **PUNTOS Y JUEGOS** | | |\n"
            "   | Total puntos ganados | [número] | [número] |\n"
            "   | Juegos ganados | [número] | [número] |\n"
            "   | Tiebreaks ganados | [número] | [número] |\n"
            "   | **RACHAS** | | |\n"
            "   | Max puntos seguidos | [número] | [número] |\n"
            "   | Max juegos seguidos | [número] | [número] |\n"
            "   \n"
            "   IMPORTANTE: NO omitas ninguna estadística. Todas deben aparecer en la tabla.\n\n"

            "==========================================\n"
            "IMPORTANTE: En tu reporte final, cuando incluyas el siguiente análisis fundamental,\n"
            "DEBES incluir expresamente el encabezado '## FUNDAMENTAL 4:' en el reporte para identificar claramente esta sección crítica.\n"
            "==========================================\n\n"

            "## FUNDAMENTAL 4: ANÁLISIS EN DIRECTO DEL SERVICIO Y PROBABILIDAD DE MANTENER EL SAQUE\n"

            "   Esta sección es CRÍTICA para predicciones. Para CADA jugador, analiza:\n\n"
            "   ### JUGADOR 1: [Nombre]\n"
            "   **A) Calidad del Servicio Actual:**\n"
            "   - % efectividad primer servicio (puntos ganados/primer servicio in)\n"
            "   - % efectividad segundo servicio (puntos ganados/segundo servicio in)\n"
            "   - Aces vs Dobles faltas (ratio)\n"
            "   - Juegos de servicio ganados vs totales\n"
            "   - Break points salvados (si los hubo)\n\n"
            "   **B) Solidez del Saque - PUNTUACIÓN 1-10:**\n"
            "   Asigna una puntuación del 1 al 10 donde:\n"
            "   - 10 = Servicio invencible, prácticamente imposible que le rompan (>80% 1er servicio ganado)\n"
            "   - 7-9 = Servicio muy sólido, difícil romperle (65-80% 1er servicio ganado)\n"
            "   - 4-6 = Servicio promedio, puede ser vulnerable (50-65% 1er servicio ganado)\n"
            "   - 1-3 = Servicio débil, alta probabilidad de ruptura (<50% 1er servicio ganado)\n"
            "   \n"
            "   **PUNTUACIÓN: [X/10]**\n"
            "   **JUSTIFICACIÓN:** [Explicación breve basada en estadísticas]\n\n"
            "   ### JUGADOR 2: [Nombre]\n"
            "   **A) Calidad del Servicio Actual:**\n"
            "   - % efectividad primer servicio (puntos ganados/primer servicio in)\n"
            "   - % efectividad segundo servicio (puntos ganados/segundo servicio in)\n"
            "   - Aces vs Dobles faltas (ratio)\n"
            "   - Juegos de servicio ganados vs totales\n"
            "   - Break points salvados (si los hubo)\n\n"
            "   **B) Solidez del Saque - PUNTUACIÓN 1-10:**\n"
            "   **PUNTUACIÓN: [X/10]**\n"
            "   **JUSTIFICACIÓN:** [Explicación breve basada en estadísticas]\n\n"
            "   **RECUERDA: Esta sección debe aparecer en tu reporte con el encabezado '## FUNDAMENTAL 4: ANÁLISIS DEL SERVICIO Y PROBABILIDAD DE MANTENER EL SAQUE'**\n\n"
            "## 5. PUNTOS DESTACADOS Y CONCLUSIONES\n"
            "   - Estadísticas más relevantes del partido\n"
            "   - Aspectos destacables de cada jugador\n"
            "   - Predicciones o tendencias basadas en los datos\n"
            "   - Información relevante para análisis de apuestas\n\n"
            "   - Finalmente rebate la estimacion y prediccion que ha hecho el agente de players en base a estos datos en directo, y sabiendo quien esta sacando, ya que por ejemplo si jugador A gana el set 6-4 sacando jugador A, ese mismo set podia haber acabado 6-4 si hubiese empezando sacando jugador B\n\n"

            "OBJETIVO PRINCIPAL:\n"
            
            "Proporcionar un análisis profesional y detallado del partido en tiempo real, útil para tomar decisiones "
            "de apuestas deportivas. Debes ser preciso con los números, analizar las tendencias y proporcionar insights "
            "valiosos basados en las estadísticas reales del partido. Finalmente rebate la estimacion y prediccion que ha hecho el agente de players en base a estos datos en directo, y sabiendo quien esta sacando, ya que por ejemplo si jugador A gana el set 6-4 sacando jugador A, ese mismo set podia haber acabado 6-4 si hubiese empezando sacando jugador B\n\n"
            "IMPORTANTE:\n"
            "- Los datos vienen formateados de Sportradar API (actualización cada 1 segundo)\n"
            "- Los nombres de jugadores vienen en formato 'Apellido, Nombre'\n"
            "- Sé preciso con todos los números y cálculos\n"
            "- Usa tablas markdown para comparar estadísticas cuando sea apropiado\n"
            "- Interpreta los datos y proporciona análisis, no solo repitas los números\n"
        )

        # Crear prompt estructurado usando la anatomía
        prompt = PromptBuilder.create_structured_prompt(
            anatomy=anatomy,
            tools_info=tools_info,
            additional_context=additional_context
        )

        # Inyección de variables al prompt
        prompt = prompt.partial(match_date=match_date)
        prompt = prompt.partial(tournament=tournament)
        prompt = prompt.partial(surface=surface)
        prompt = prompt.partial(player_a=player_a)
        prompt = prompt.partial(player_b=player_b)

        # Construcción de la cadena LLM con herramientas
        chain = prompt | llm.bind_tools(tools)

        # Crear el input correcto como diccionario
        input_data = {
            "messages": state[STATE.messages],
            "user_message": f"Obtén información en tiempo real del partido {player_a} vs {player_b} del torneo {tournament} usando Sportradar API."
        }

        result = chain.invoke(input_data)

        # Generar reporte basado en el resultado
        report = result.content
        if hasattr(result, 'tool_calls') and result.tool_calls:
            # Si hay tool calls, el contenido puede estar en el resultado final
            report = result.content

        return {
            STATE.messages: [result],
            REPORTS.match_live_report: report,
        }

    return match_live_analyst_node
