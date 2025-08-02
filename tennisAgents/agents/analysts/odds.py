from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tennisAgents.utils.enumerations import *

def create_odds_analyst(llm, toolkit):
    def odds_analyst_node(state):
        match_date = state[STATE.match_date]
        player = state[STATE.player_of_interest]
        opponent = state[STATE.opponent]
        tournament = state[STATE.tournament]

        if toolkit.config["online_tools"]:
            tools = [toolkit.get_odds_data]
        else:
            tools = [toolkit.get_mock_odds_data]

        # Lista de torneos disponibles como string para el agente
        tournament_keys = """
TORNEOS DISPONIBLES EN THE ODDS API:

ATP Tournaments:
- australian_open → tennis_atp_aus_open_singles
- french_open → tennis_atp_french_open
- wimbledon → tennis_atp_wimbledon
- us_open → tennis_atp_us_open
- indian_wells → tennis_atp_indian_wells
- miami_open → tennis_atp_miami_open
- monte_carlo → tennis_atp_monte_carlo_masters
- madrid_open → tennis_atp_madrid_open
- italian_open → tennis_atp_italian_open
- canadian_open → tennis_atp_canadian_open
- cincinnati_open → tennis_atp_cincinnati_open
- shanghai_masters → tennis_atp_shanghai_masters
- paris_masters → tennis_atp_paris_masters
- dubai → tennis_atp_dubai
- qatar_open → tennis_atp_qatar_open
- china_open → tennis_atp_china_open

WTA Tournaments:
- wta_australian_open → tennis_wta_aus_open_singles
- wta_french_open → tennis_wta_french_open
- wta_wimbledon → tennis_wta_wimbledon
- wta_us_open → tennis_wta_us_open
- wta_indian_wells → tennis_wta_indian_wells
- wta_miami_open → tennis_wta_miami_open
- wta_madrid_open → tennis_wta_madrid_open
- wta_italian_open → tennis_wta_italian_open
- wta_canadian_open → tennis_wta_canadian_open
- wta_cincinnati_open → tennis_wta_cincinnati_open
- wta_dubai → tennis_wta_dubai
- wta_qatar_open → tennis_wta_qatar_open
- wta_china_open → tennis_wta_china_open
- wta_wuhan_open → tennis_wta_wuhan_open
"""

        system_message = (
            f"Eres un analista de apuestas deportivas. Tu tarea es examinar las cuotas ofrecidas por las casas de apuestas "
            f"para el partido entre {player} y {opponent} que se disputa el {match_date} en el torneo {tournament}.\n\n"
            f"{tournament_keys}\n\n"
            "PROCESO A SEGUIR:\n"
            "1. Basándote en la fecha del partido ({match_date}) y el tipo de jugadores, selecciona el torneo más relevante de la lista anterior.\n"
            "2. Usa 'get_odds_data' con el tournament_key correspondiente (la parte después de →).\n"
            "3. Busca en los eventos del torneo el partido específico entre los jugadores.\n\n"
            "ANÁLISIS REQUERIDO:\n"
            "- Qué jugador parte como favorito según las cuotas.\n"
            "- Qué casas ofrecen cuotas significativamente distintas.\n"
            "- Si las cuotas han variado en las últimas horas y qué puede significar eso.\n"
            "- Cualquier patrón que indique que el mercado apuesta fuertemente a una dirección.\n\n"
            "Al final del informe, añade una tabla Markdown con las cuotas por casa y cualquier observación clave."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Actúas como parte de un sistema de IA que asiste en la predicción de partidos de tenis. "
                    "Tu enfoque es el análisis de mercados de apuestas. Colabora con otros agentes y proporciona observaciones valiosas usando las herramientas disponibles:\n\n"
                    "{tool_names}\n\n"
                    "{system_message}"
                ),
                ("user", "Analiza las cuotas de apuestas para el partido entre {player} y {opponent}."),
                MessagesPlaceholder(variable_name=STATE.messages),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(player=player)
        prompt = prompt.partial(opponent=opponent)

        chain = prompt | llm.bind_tools(tools)
        
        result = chain.invoke(state[STATE.messages])

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            STATE.messages: [result],
            REPORTS.odds_report: report,
        }

    return odds_analyst_node
