from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tennisAgents.utils.enumerations import *

def create_news_analyst(llm, toolkit):
    def news_analyst_node(state):
        current_date = state[STATE.match_date]
        player = state[STATE.player_of_interest]
        opponent = state[STATE.opponent]
        tournament = state[STATE.tournament]

        # Herramientas según configuración
        if toolkit.config["online_tools"]:
            tools = [toolkit.get_news]
        else:
            tools = [
                toolkit.get_atp_news,
                toolkit.get_tennisworld_news,
                toolkit.get_news,
            ]

        system_message = (
            f"Eres un analista de noticias especializado en tenis profesional. Tu misión es investigar y generar un informe detallado sobre las noticias más relevantes "
            f"de los últimos días relacionadas con el torneo {tournament}, en especial sobre los jugadores {player} y {opponent}. "
            "Debes identificar cualquier información crítica como lesiones, cambios de entrenador, declaraciones polémicas, presión mediática, etc., que puedan influir en su rendimiento.\n\n"
            "Incluye noticias generales del circuito ATP/WTA si son relevantes para la lectura del partido. Finaliza con una tabla Markdown que resuma los puntos clave para facilitar la lectura."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Eres un asistente experto en analizar noticias deportivas y colaborar con otros agentes de IA. "
                    "Tu objetivo es reunir información que pueda ser útil para predecir el desempeño de los jugadores.\n\n"
                    "Usa las siguientes herramientas: {tool_names}.\n{system_message}\n\n"
                    "Fecha actual: {current_date}. Jugadores: {player} vs {opponent}, Torneo: {tournament}."
                ),
                ("user", "Analiza las noticias más relevantes sobre {player} y {opponent} para el torneo {tournament}."),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        # Rellenamos variables dinámicas
        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(player=player)
        prompt = prompt.partial(opponent=opponent)
        prompt = prompt.partial(tournament=tournament)

        chain = prompt | llm.bind_tools(tools)

        # Convertir los mensajes al formato correcto para LangChain
        messages = []
        for msg in state["messages"]:
            if isinstance(msg, tuple):
                role, content = msg
                if role == "human":
                    messages.append({"role": "user", "content": content})
                elif role == "ai":
                    messages.append({"role": "assistant", "content": content})
            else:
                messages.append(msg)

        result = chain.invoke({"messages": messages})

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            REPORTS.news_report: report,
        }

    return news_analyst_node
