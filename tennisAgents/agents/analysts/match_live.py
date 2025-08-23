from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies

def create_match_live_analyst(llm, toolkit):
    def match_live_analyst_node(state):
        match_date = state[STATE.match_date]
        player_a = state[STATE.player_of_interest]
        player_b = state[STATE.opponent]
        tournament = state[STATE.tournament]
        surface = state.get(STATE.surface, "")

        # Herramienta para obtener datos ficticios del partido en vivo
        tools = [toolkit.get_mock_match_live_data]
        
        # Obtener la anatomía del prompt para analista de partidos en vivo
        anatomy = TennisAnalystAnatomies.match_live_analyst()
        
        # Información de herramientas
        tools_info = (
            "• get_mock_match_live_data(player_a, player_b, tournament) - Genera datos ficticios realistas del partido en vivo incluyendo score, estadísticas y momentum"
        )
        
        # Contexto adicional específico del análisis en tiempo real
        additional_context = (
            "PROCESO OBLIGATORIO:\n"
            f"1. DEBES usar UNA UNICA VEZ la herramienta 'get_mock_match_live_data' con estos parámetros EXACTOS:\n"
            f"   - player_a: '{player_a}'\n"
            f"   - player_b: '{player_b}'\n"
            f"   - tournament: '{tournament}'\n"
            "2. NO procedas sin llamar a la herramienta primero\n"
            "3. Una vez que obtengas los datos, analiza el estado actual del partido que se está jugando en directo\n\n"
            "ANÁLISIS REQUERIDO:\n"
            "• Estado actual del partido en directo(score, sets ganados, momento actual del partido)\n"
            "• Estadísticas en tiempo real (aces, dobles faltas, porcentajes de servicio)\n"
            "• Análisis táctico de ambos jugadores durante el partido\n"
            "• Evaluación del momento actual del partido\n"
            "• Identificación de patrones emergentes durante el partido\n"
            "• Predicciones basadas en el desarrollo actual del juego\n"
            "• Oportunidades de trading basadas en el estado del partido\n\n"
            "INFORMACIÓN OBLIGATORIA EN LA SALIDA:\n"
            "1. Información general:\n"
            "   - Nombre del torneo y la fase (ej. US Open – Qualifying Round).\n"
            "   - Fecha y lugar de juego (si está disponible).\n"
            "   - Estado del partido (en curso, finalizado, próximo).\n\n"
            "2. Marcador en vivo:\n"
            "   - Resultados por set (ejemplo: 7-6, 3-6, 4-2 en curso).\n"
            "   - Tie-breaks detallados si se jugaron.\n"
            "   - Indicar si un set o el partido está en curso.\n\n"
            "3. Estadísticas del partido:\n"
            "   - Aces, dobles faltas.\n"
            "   - Porcentaje de primeros y segundos saques.\n"
            "   - Puntos ganados con primer/segundo saque.\n"
            "   - Break points convertidos / totales.\n"
            "   - Total de puntos ganados.\n"
            "   - Juegos de servicio ganados/perdidos.\n"
            "   - Rachas de puntos o juegos (si están disponibles).\n\n"
            "IMPORTANTE:\n"
            "• Proporciona análisis específico con datos concretos del partido actual\n"
            "• Enfócate en información en tiempo real, no en datos históricos\n"
            "• Identifica cambios significativos que puedan afectar las cuotas\n"
            "• Evalúa el impacto de las condiciones externas en el desarrollo del juego\n"
            "• Asegúrate de que tu análisis incluya TODA la información requerida arriba\n\n"
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
            "user_message": f"Analiza el estado actual del partido entre {player_a} y {player_b} en el torneo {tournament}. Obtén datos del partido en vivo y analiza el desarrollo del juego."
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
