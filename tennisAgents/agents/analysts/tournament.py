from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tennisAgents.utils.enumerations import *

def create_tournament_analyst(llm, toolkit):
    def tournament_analyst_node(state):
        match_date = state[STATE.match_date]
        tournament = state[STATE.tournament]
        location = state.get(STATE.location, "Ubicación no especificada")
        player = state[STATE.player_of_interest]
        opponent = state[STATE.opponent]

        # Herramientas específicas
        if toolkit.config["online_tools"]:
            tools = [toolkit.get_tournament_info]
        else:
            tools = [toolkit.get_tournament_info]

        # Mensaje principal
        system_message = (
            f"Eres un experto analista de torneos de tenis. Tu tarea es realizar un informe detallado del torneo '{tournament}', "
            f"que se celebra en {location} el día {match_date}."
        )

        # Plantilla del prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Eres un asistente especializado en análisis de torneos de tenis. "
                    "Colaboras con otros agentes para tomar decisiones basadas en el torneo actual.\n\n"
                    "Herramientas: {tool_names}\n\n"
                    "{system_message}\n\n"
                    "FACTORES A EVALUAR:\n"
                    "• Tipo de superficie y condiciones físicas del entorno (altitud, clima habitual, velocidad de la pista)\n"
                    "• Categoría del torneo y su importancia en el calendario\n"
                    "• Historial de {player} y {opponent} en este torneo o en condiciones similares\n"
                    "• Impacto del formato del torneo en el rendimiento de los jugadores\n\n"
                    "CONOCIMIENTO ESPECÍFICO DEL TENIS:\n"
                    "• Categorías de torneos: atpgs (ATP + Grand Slams), atp (circuito ATP), gs (Grand Slams), 1000 (Masters 1000), ch (Challenger Circuit)\n"
                    "• En Grand Slams: los jugadores juegan en días alternos, afectando la fatiga y recuperación\n"
                    "• En Grand Slams avanzados: el jugador con mejor ranking/trayectoria suele ganar por mayor confianza y menos nervios (mejor de 5 sets)\n"
                    "• En torneos menores: los jugadores buenos pueden no rendir al máximo si se reservan para torneos importantes\n"
                    "• Jugadores mayores de 30 años: menor disposición para remontar partidos/sets, especialmente en formato a 5 sets\n\n"
                    "OBJETIVO: Ayudar al equipo de predicción a entender el impacto del torneo sobre el rendimiento de los jugadores.\n\n"
                    "IMPORTANTE: Solo puedes hacer UNA SOLA LLAMADA a get_tournament_info. Usa esa información de manera eficiente y completa.\n\n"
                    "FORMATO DEL INFORME:\n"
                    "1. Resumen ejecutivo del torneo y su contexto\n"
                    "2. Análisis de la superficie y condiciones ambientales\n"
                    "3. Importancia del torneo y su impacto en la motivación\n"
                    "4. Historial de los jugadores en este tipo de torneos\n"
                    "5. Factores específicos que pueden influir en el resultado\n"
                    "6. Tabla Markdown con factores clave organizados por categoría\n\n"
                    "IMPORTANTE: Proporciona análisis específico y contextual, no generalidades. Incluye fechas relevantes, estadísticas concretas y contexto específico del torneo.\n\n"
                    "IMPORTANTE: Cuando uses get_tournament_info, debes incluir la fecha del partido {match_date} como parámetro 'date'."
                ),
                ("user", "Analiza el torneo {tournament} en {location} y su impacto en {player} y {opponent}."),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(tournament=tournament)
        prompt = prompt.partial(location=location)
        prompt = prompt.partial(player=player)
        prompt = prompt.partial(opponent=opponent)
        prompt = prompt.partial(match_date=match_date)

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
            REPORTS.tournament_report: report,
        }

    return tournament_analyst_node
