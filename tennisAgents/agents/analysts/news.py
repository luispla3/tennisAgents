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
                toolkit.get_news,
            ]

        system_message = (
            f"Eres un analista de noticias especializado en tenis profesional. Tu misión es investigar y generar un informe detallado sobre las noticias más relevantes "
            f"de los últimos días relacionadas con el torneo {tournament}, en especial sobre los jugadores {player} y {opponent}."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Eres un asistente experto en analizar noticias deportivas y colaborar con otros agentes de IA. "
                    "Tu objetivo es reunir información que pueda ser útil para predecir el desempeño de los jugadores.\n\n"
                    "Herramientas disponibles: {tool_names}\n\n"
                    "{system_message}\n\n"
                    "OBJETIVO: Identificar información crítica que pueda influir en el rendimiento de los jugadores, incluyendo:\n"
                    "• Lesiones recientes o problemas físicos, sobretodo en los partidos anteriores de ese toreno si los hay, para ello habra que investigar bien en las noticias\n"
                    "• Cambios de entrenador o equipo técnico\n"
                    "• Declaraciones polémicas o presión mediática\n"
                    "• Estado mental o motivacional\n"
                    "• Rendimiento en torneos recientes\n"
                    "• Rivalidades o historial personal\n\n"
                    "INSTRUCCIONES TÉCNICAS:\n"
                    "• Para búsquedas con get_news: usa ÚNICAMENTE el nombre del jugador (ej: 'Christopher O'Connell', NO 'Christopher O'Connell 2025 Motorola razr Grandstand Court')\n"
                    "• Incluye noticias generales del circuito ATP/WTA si son relevantes para el análisis del partido\n\n"
                    "FORMATO DEL INFORME:\n"
                    "1. Resumen ejecutivo de las noticias más impactantes\n"
                    "2. Análisis detallado por jugador\n"
                    "3. Contexto del torneo y su relevancia\n"
                    "4. Implicaciones para el partido\n"
                    "5. Tabla Markdown con puntos clave organizados por categoría\n\n"
                    "IMPORTANTE: Proporciona análisis granular y específico, no generalidades como 'las tendencias son mixtas'. Incluye fechas, citas relevantes y contexto específico.\n\n"
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
            REPORTS.news_report: report,
        }

    return news_analyst_node
