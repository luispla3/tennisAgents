from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies

def create_weather_analyst(llm, toolkit):
    def weather_analyst_node(state):
        match_date = state[STATE.match_date]
        location = state.get(STATE.location, "Ubicación no especificada")
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
            "• get_weather_forecast(tournament, fecha_hora, location) - Obtiene pronóstico meteorológico para una ubicación y fecha específicas\n\n"
            "INFORMACIÓN DISPONIBLE:\n"
            f"• Fecha del partido: {match_date}\n"
            f"• Ubicación: {location}\n"
            f"• Torneo: {tournament}\n"
            f"• Jugadores: {player} vs {opponent}"
        )
        
        # Contexto adicional específico del análisis del clima
        additional_context = (
            "INSTRUCCIONES ESPECÍFICAS:\n"
            f"• Usa la fecha del partido: {match_date}\n"
            f"• Usa la ubicación: {location}\n"
            f"• Usa el nombre del torneo: {tournament}\n"
            f"• Procede DIRECTAMENTE con el análisis usando get_weather_forecast\n"
            "• NO pidas información adicional al usuario\n\n"
            "FACTORES CLIMÁTICOS A ANALIZAR:\n"
            "• Temperatura y su impacto en la velocidad de la pelota y resistencia de los jugadores\n"
            "• Viento y su efecto en la precisión de los saques y golpes\n"
            "• Humedad y su influencia en la velocidad de la superficie y deslizamiento\n"
            "• Posibilidad de lluvia y su impacto en la continuidad del juego\n"
            "• Presión atmosférica y su efecto en la altitud (si aplica)\n\n"
            "ANÁLISIS REQUERIDO:\n"
            "• Cómo las condiciones climáticas pueden afectar el estilo de juego de ambos jugadores\n"
            "• Historial de rendimiento de los jugadores bajo condiciones climáticas similares\n"
            "• Impacto en la estrategia del partido y adaptaciones necesarias\n"
            "• Comparación de ventajas/desventajas para cada jugador según el clima\n\n"
            "IMPORTANTE: Haz solo una llamada a get_weather_forecast y usa la información de manera eficiente y completa.\n"
            "IMPORTANTE: Procede DIRECTAMENTE con el análisis usando la información disponible.\n"
            "IMPORTANTE: NO pidas información adicional al usuario."
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
        prompt = prompt.partial(location=location)
        prompt = prompt.partial(match_date=match_date)
        prompt = prompt.partial(tournament=tournament)

        # Construcción de la cadena LLM con herramientas
        chain = prompt | llm.bind_tools(tools)

        # Crear el input correcto como diccionario
        input_data = {
            "messages": state[STATE.messages],
            "user_message": f"Analiza las condiciones meteorológicas para el partido entre {player} y {opponent} en {location} el día {match_date}."
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
