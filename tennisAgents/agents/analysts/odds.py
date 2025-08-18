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
            f"Eres un analista de apuestas deportivas especializado en tenis. Tu tarea es examinar las cuotas ofrecidas por las casas de apuestas "
            f"para el partido entre {player} y {opponent} que se disputa el {match_date} en el torneo {tournament}."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Actúas como parte de un sistema de IA que asiste en la predicción de partidos de tenis. "
                    "Tu enfoque es el análisis de mercados de apuestas para proporcionar insights valiosos.\n\n"
                    "Herramientas: {tool_names}\n\n"
                    "{system_message}\n\n"
                    f"{tournament_keys}\n\n"
                    "PROCESO A SEGUIR:\n"
                    "1. Basándote en la fecha del partido ({match_date}) y el tipo de jugadores, selecciona el torneo más relevante de la lista anterior.\n"
                    "2. Usa 'get_odds_data' con el tournament_key correspondiente (la parte después de →).\n"
                    "3. Busca en los eventos del torneo el partido específico entre los jugadores.\n\n"
                    "ANÁLISIS REQUERIDO:\n"
                    "• Identificación del favorito según las cuotas y margen de ventaja\n"
                    "• Comparación de cuotas entre diferentes casas de apuestas\n"
                    "• Análisis de variaciones en las cuotas (si están disponibles)\n"
                    "• Patrones que indiquen confianza del mercado en una dirección\n"
                    "• Discrepancias significativas entre casas que puedan indicar oportunidades\n"
                    "• Contexto del torneo y su impacto en las cuotas\n\n"
                    "FORMATO DEL INFORME:\n"
                    "1. Resumen ejecutivo de las cuotas y favorito\n"
                    "2. Análisis detallado por casa de apuestas\n"
                    "3. Comparación de márgenes y diferencias\n"
                    "4. Interpretación de las tendencias del mercado\n"
                    "5. Tabla Markdown con cuotas organizadas por casa y observaciones clave\n\n"
                    "IMPORTANTE: Proporciona análisis específico con números concretos, no generalidades. Incluye cuotas exactas, márgenes calculados y contexto específico del mercado."
                ),
                ("user", "Analiza las cuotas de apuestas para el partido entre {player} y {opponent}."),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
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
            REPORTS.odds_report: report,
        }

    return odds_analyst_node
