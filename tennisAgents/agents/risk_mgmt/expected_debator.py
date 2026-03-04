from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, RiskManagerAnatomies

def create_expected_debator(llm):
    def expected_node(state) -> dict:
        risk_debate_state = state[STATE.risk_debate_state]
        history = risk_debate_state.get(HISTORYS.history, "")
        expected_history = risk_debate_state.get(HISTORYS.expected_history, "")

        current_aggressive_response = risk_debate_state.get(RESPONSES.aggressive, "")
        current_neutral_response = risk_debate_state.get(RESPONSES.neutral, "")
        current_safe_response = risk_debate_state.get(RESPONSES.safe, "")

        # Informes disponibles
        weather_report = state[REPORTS.weather_report]
        odds_report = state[REPORTS.odds_report]
        sentiment_report = state[REPORTS.sentiment_report]
        news_report = state[REPORTS.news_report]
        players_report = state[REPORTS.players_report]
        tournament_report = state[REPORTS.tournament_report]
        match_live_report = state.get(REPORTS.match_live_report, "")

        # Información del usuario y partido
        wallet_balance = state.get(STATE.wallet_balance, 0)
        match_date = state.get(STATE.match_date, "")
        player_of_interest = state.get(STATE.player_of_interest, "")
        opponent = state.get(STATE.opponent, "")
        tournament = state.get(STATE.tournament, "")

        # Construir el contexto dinámico
        additional_context = f"""
**INFORMACIÓN DEL PARTIDO:**
- Fecha del partido: {match_date}
- Jugador de interés: {player_of_interest}
- Oponente: {opponent}
- Torneo: {tournament}
- Superficie: la superficie del torneo
- Saldo disponible: ${wallet_balance}

**INFORMES DISPONIBLES:**
- Pronóstico del tiempo: {weather_report}
- Informe de cuotas de apuestas: {odds_report}
- Sentimiento en redes sociales: {sentiment_report}
- Noticias recientes: {news_report}
- Estado físico y mental de los jugadores: {players_report}
- Información del torneo: {tournament_report}
- Estado del partido en vivo: {match_live_report}

**ARGUMENTOS PREVIOS DE OTROS ANALISTAS:**
- Analista agresivo: {current_aggressive_response}
- Analista neutral: {current_neutral_response}
- Analista seguro: {current_safe_response}

**HISTORIAL DE DEBATE:**
{history}
"""

        # Obtener la anatomía y crear el prompt
        anatomy = RiskManagerAnatomies.expected_debator()
        prompt = PromptBuilder.create_structured_prompt(
            anatomy=anatomy,
            additional_context=additional_context
        )

        # Invocar al LLM
        response = llm.invoke(prompt.invoke({"user_message": "Realiza tu análisis matemático de valor esperado y debate con los otros analistas."}))

        argument = f"Expected Value Analyst: {response.content}"

        new_risk_debate_state = {
            HISTORYS.history: history + "\n" + argument,
            HISTORYS.aggressive_history: risk_debate_state.get(HISTORYS.aggressive_history, ""),
            HISTORYS.safe_history: risk_debate_state.get(HISTORYS.safe_history, ""),
            HISTORYS.neutral_history: risk_debate_state.get(HISTORYS.neutral_history, ""),
            HISTORYS.expected_history: expected_history + "\n" + argument,
            STATE.latest_speaker: SPEAKERS.expected,
            RESPONSES.aggressive: risk_debate_state.get(RESPONSES.aggressive, ""),
            RESPONSES.safe: risk_debate_state.get(RESPONSES.safe, ""),
            RESPONSES.neutral: risk_debate_state.get(RESPONSES.neutral, ""),
            RESPONSES.expected: argument,
            STATE.count: risk_debate_state.get(STATE.count, 0) + 1,
        }

        return {STATE.risk_debate_state: new_risk_debate_state}

    return expected_node
