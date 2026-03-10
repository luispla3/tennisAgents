from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies

def create_weather_analyst(llm, toolkit):
    def weather_analyst_node(state):
        match_date = state[STATE.match_date]
        player = state[STATE.player_of_interest]
        opponent = state[STATE.opponent]
        tournament = state[STATE.tournament]

        # Herramientas de consulta meteorológica
        if toolkit.config["online_tools"]:
            tools = [toolkit.get_weather_forecast]
        else:
            tools = [toolkit.get_weather_forecast]  # Para testing o entorno offline

        # Obtener la anatomía del prompt para analista del clima
        anatomy = TennisAnalystAnatomies.weather_analyst()
        
        # Información de herramientas
        tools_info = (
            "• get_weather_forecast(tournament, fecha_hora, location) - Obtiene pronóstico meteorológico para una ubicación y fecha específicas.\n\n"
            "INFORMACIÓN DISPONIBLE:\n"
            f"• Fecha del partido: {match_date}\n"
            f"• Torneo: {tournament}\n"
            f"• Jugadores: {player} vs {opponent}"
        )
        
        # Contexto adicional específico del análisis del clima
        additional_context = (
            "INSTRUCCIONES ESPECÍFICAS:\n"
            f"• Usa la fecha del partido: {match_date}\n"
            f"• Usa el nombre del torneo: {tournament}\n"
            f"• Procede DIRECTAMENTE con la consulta usando get_weather_forecast\n"
            "• NO pidas información adicional al usuario\n\n"
            "INFORMACIÓN METEOROLÓGICA A REPORTAR:\n"
            "• Temperatura prevista\n"
            "• Viento previsto\n"
            "• Humedad prevista\n"
            "• Posibilidad de lluvia\n"
            "• Presión atmosférica, nubosidad u otras variables disponibles\n\n"
            "INTERPRETACIÓN OBJETIVA PERMITIDA:\n"
            "• Puedes describir efectos físicos generales de las condiciones sobre el entorno de juego\n"
            "• Limítate a relaciones generales y verificables, sin atribuir ventajas concretas a un jugador\n"
            "• No uses historial de rendimiento de jugadores bajo clima similar si no está disponible en la herramienta\n"
            "• No hagas predicciones ni recomendaciones estratégicas\n\n"
            "IMPORTANTE: Haz solo una llamada a get_weather_forecast y usa la información de manera eficiente y completa.\n"
            "IMPORTANTE: Procede DIRECTAMENTE con la información disponible.\n"
            "IMPORTANTE: NO pidas información adicional al usuario.\n"
            "IMPORTANTE: Si falta algún dato meteorológico, indícalo explícitamente como no disponible."
        )

        # Crear prompt estructurado usando la anatomía
        prompt = PromptBuilder.create_structured_prompt(
            anatomy=anatomy,
            tools_info=tools_info,
            additional_context=additional_context
        )

        # Inyección de variables al prompt
        prompt = prompt.partial(player=player)
        prompt = prompt.partial(opponent=opponent)
        prompt = prompt.partial(match_date=match_date)
        prompt = prompt.partial(tournament=tournament)

        # Construcción de la cadena LLM con herramientas
        chain = prompt | llm.bind_tools(tools)

        # Crear el input correcto como diccionario
        input_data = {
            "messages": state[STATE.messages],
            "user_message": f"Recopila y presenta las condiciones meteorológicas previstas para el partido entre {player} y {opponent} el día {match_date}."
        }

        result = chain.invoke(input_data)

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            STATE.messages: [result],
            REPORTS.weather_report: report,
        }

    return weather_analyst_node
