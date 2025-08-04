from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tennisAgents.utils.enumerations import *

def create_tournament_analyst(llm, toolkit):
    def tournament_analyst_node(state):
        match_date = state[STATE.match_date]
        tournament = state[STATE.tournament]
        location = state.get(STATE.location, "London")
        player = state[STATE.player_of_interest]
        opponent = state[STATE.opponent]

        # Herramientas específicas
        if toolkit.config["online_tools"]:
            tools = [toolkit.get_tournament_info]
        else:
            tools = [toolkit.get_mock_tournament_data]

        # Mensaje principal
        system_message = (
            f"Eres un experto analista de torneos de tenis. Debes realizar un informe detallado del torneo '{tournament}', "
            f"que se celebra en {location} el día {match_date}. Evalúa factores como el tipo de superficie, condiciones físicas del entorno "
            f"(altitud, clima habitual, velocidad de la pista), tipo de torneo, y el historial de {player} y {opponent} en este torneo o en condiciones similares.\n\n"
            "Tu objetivo es ayudar al equipo de predicción a entender el impacto del torneo sobre el rendimiento de los jugadores.\n"
            "Al final, incluye una tabla Markdown clara con los factores clave extraídos del análisis.\n\n"
            "IMPORTANTE: la variable category es la categoria del torneo, y tienes que usar la que corresponda: Categoría del torneo: atpgs: Atp tournaments + grand Slams, atp: Atp circuit, gs: grand slams, 1000: Masters 1000, ch: Challenger Circuit"
            "IMPORTANTE: Solo puedes hacer UNA SOLA LLAMADA a get_tournament_info. Usa esa información de manera eficiente y completa.\n\n"
            "IMPORTANTE: debes saber que en los torenos Grand Slam, los jugadores no juegan en el mismo día, sino que juegan en días alternos, por lo que debes tener en cuenta que el jugador que juega el día anterior puede estar cansado y que el jugador que juega el día siguiente puede estar en mejor forma."
            "IMPORTANTE: debes saber que en los torneos Grand Slam, y en concreto a medida que avanza el torneo, el jugador con mejor ranking o con mejor trayectoria suele ganar el partido porque tiene menos nervios y es más confiado, y se juega al mejor de 5 sets. Se nota sobretodo en los partidos, juegos y puntos críticos."
            "IMPORTANTE: Tambien debes saber que en los torneos que no son especialmente importantes, los jugadores buenos tienden a no hacer los resultados esperados, sobretodo si se acerca otro torneo importante, para reservarse fisicamente y mentalmente para el torneo importante. O de la misma forma, si han jugado un campeonato importante y vienen cansados, tienden a no hacer los resultados esperados."
            "IMPORTANTE: Debes tener en cuenta la edad de los jugadores, si son mayores de 30 años, sobretodo en campeonatos a 5 sets, dependiendo tambien de su forma de juego, si son defensivos o ofensivos, etc., de lo cansado que esten, puede que ya no esten dispuestos a remontar partidos, sets, etc"
        )

        # Plantilla del prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Eres un asistente especializado en análisis de torneos de tenis. "
                    "Colaboras con otros agentes para tomar decisiones basadas en el torneo actual.\n\n"
                    "Usa las herramientas disponibles para obtener información detallada:\n\n"
                    "IMPORTANTE: la variable category es la categoria del torneo, y tienes que usar la que corresponda: Categoría del torneo: atpgs: Atp tournaments + grand Slams, atp: Atp circuit, gs: grand slams, 1000: Masters 1000, ch: Challenger Circuit"
                    "IMPORTANTE: Solo puedes hacer UNA SOLA LLAMADA a get_tournament_info. Usa esa información de manera eficiente y completa.\n\n"
                    "IMPORTANTE: debes saber que en los torenos Grand Slam, los jugadores no juegan en el mismo día, sino que juegan en días alternos, por lo que debes tener en cuenta que el jugador que juega el día anterior puede estar cansado y que el jugador que juega el día siguiente puede estar en mejor forma."
                    "IMPORTANTE: debes saber que en los torneos Grand Slam, y en concreto a medida que avanza el torneo, el jugador con mejor ranking o con mejor trayectoria suele ganar el partido porque tiene menos nervios y es más confiado, y se juega al mejor de 5 sets. Se nota sobretodo en los partidos, juegos y puntos críticos."
                    "IMPORTANTE: Tambien debes saber que en los torneos que no son especialmente importantes, los jugadores buenos tienden a no hacer los resultados esperados, sobretodo si se acerca otro torneo importante, para reservarse fisicamente y mentalmente para el torneo importante. O de la misma forma, si han jugado un campeonato importante y vienen cansados, tienden a no hacer los resultados esperados."
                    "IMPORTANTE: Debes tener en cuenta la edad de los jugadores, si son mayores de 30 años, sobretodo en campeonatos a 5 sets, dependiendo tambien de su forma de juego, si son defensivos o ofensivos, etc., de lo cansado que esten, puede que ya no esten dispuestos a remontar partidos, sets, etc"

                    "{tool_names}\n\n"
                    "{system_message}"
                ),
                ("user", "Analiza el torneo {tournament} en {location} y su impacto en {player} y {opponent}."),
                MessagesPlaceholder(variable_name=STATE.messages),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(tournament=tournament)
        prompt = prompt.partial(location=location)
        prompt = prompt.partial(player=player)
        prompt = prompt.partial(opponent=opponent)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state[STATE.messages])

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            STATE.messages: [result],
            REPORTS.tournament_report: report,
        }

    return tournament_analyst_node
