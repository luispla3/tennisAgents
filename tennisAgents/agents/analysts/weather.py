from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tennisAgents.utils.enumerations import *

def create_weather_analyst(llm, toolkit):
    def weather_analyst_node(state):
        match_date = state[STATE.match_date]
        location = state.get(STATE.location, "Wimbledon")
        player = state[STATE.player_of_interest]
        opponent = state[STATE.opponent]
        tournament = state[STATE.tournament]

        # Herramientas de consulta meteorológica
        if toolkit.config["online_tools"]:
            tools = [toolkit.get_weather_forecast]
        else:
            tools = [toolkit.get_mock_weather_data]  # Para testing o entorno offline

        # Mensaje al sistema para enfocar el análisis
        system_message = (
            f"Eres un analista meteorológico especializado en tenis. Tu tarea es evaluar las condiciones climáticas "
            f"esperadas para el día {match_date} en {location}, sede del torneo {tournament}, donde jugarán {player} contra {opponent}."
        )

        # Definición del prompt con historial y herramientas
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Eres un asistente experto en meteorología deportiva colaborando con otros analistas. "
                    "Tu objetivo es analizar el impacto del clima en el rendimiento de los jugadores de tenis.\n\n"
                    "Herramientas: {tool_names}\n\n"
                    "{system_message}\n\n"
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
                    "IMPORTANTE: Haz solo una llamada a get_weather_forecast y usa la información de manera eficiente y completa.\n\n"
                    "FORMATO DEL INFORME:\n"
                    "1. Resumen ejecutivo de las condiciones climáticas esperadas\n"
                    "2. Análisis detallado de cada factor meteorológico\n"
                    "3. Impacto específico en el estilo de juego de cada jugador\n"
                    "4. Adaptaciones estratégicas recomendadas\n"
                    "5. Tabla Markdown con factores clave organizados por categoría\n\n"
                    "IMPORTANTE: Proporciona análisis específico y cuantitativo, no generalidades. Incluye temperaturas exactas, velocidades de viento, porcentajes de humedad y contexto específico del impacto en el tenis.\n\n"
                    "IMPORTANTE: Las coordenadas latitud y longitud corresponden a la ubicación del torneo, y la fecha y hora son las del partido."
                ),
                ("user", "Analiza las condiciones meteorológicas para el partido entre {player} y {opponent} en {location}."),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        # Rellenar con valores reales del estado
        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(player=player)
        prompt = prompt.partial(opponent=opponent)
        prompt = prompt.partial(location=location)

        chain = prompt | llm.bind_tools(tools)

        # Crear el input correcto como diccionario
        input_data = {
            "messages": state[STATE.messages]
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
