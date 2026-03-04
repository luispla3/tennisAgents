from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, RiskManagerAnatomies

def create_aggressive_debator(llm):
    def aggressive_node(state) -> dict:
        risk_debate_state = state[STATE.risk_debate_state]
        history = risk_debate_state.get(HISTORYS.history, "")
        aggressive_history = risk_debate_state.get(HISTORYS.aggressive_history, "")

        current_neutral_response = risk_debate_state.get(RESPONSES.neutral, "")
        current_safe_response = risk_debate_state.get(RESPONSES.safe, "")
        current_expected_response = risk_debate_state.get(RESPONSES.expected, "")

        # Informes disponibles
        news_report = state[REPORTS.news_report]
        odds_report = state[REPORTS.odds_report]
        players_report = state[REPORTS.players_report]
        sentiment_report = state[REPORTS.sentiment_report]
        tournament_report = state[REPORTS.tournament_report]
        weather_report = state[REPORTS.weather_report]
        match_live_report = state.get(REPORTS.match_live_report, "")
        
        # Información del usuario y partido
        wallet_balance = state.get(STATE.wallet_balance, 0)
        match_date = state.get(STATE.match_date, "")
        player_of_interest = state.get(STATE.player_of_interest, "")
        opponent = state.get(STATE.opponent, "")
        tournament = state.get(STATE.tournament, "")

        # Construir el contexto dinámico
        additional_context = f"""
**INFORMACIÓN DEL USUARIO Y PARTIDO:**
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
- Analista conservadora: {current_safe_response}
- Analista neutral: {current_neutral_response}
- Analista de probabilidades: {current_expected_response}

**HISTORIAL DE DEBATE:**
{history}
"""

        # Obtener la anatomía y crear el prompt
        anatomy = RiskManagerAnatomies.aggressive_debator()
        prompt = PromptBuilder.create_structured_prompt(
            anatomy=anatomy,
            additional_context=additional_context
        )

        # Invocar al LLM
        # Como PromptBuilder crea un ChatPromptTemplate que espera 'user_message', 
        # proporcionamos una instrucción de activación.
        response = llm.invoke(prompt.invoke({"user_message": "Genera tu análisis agresivo y estrategia de inversión basada en la información proporcionada."}))

        argument = f"Aggressive Analyst: {response.content}"

        new_risk_debate_state = {
            HISTORYS.history: history + "\n" + argument,
            HISTORYS.aggressive_history: aggressive_history + "\n" + argument,
            HISTORYS.safe_history: risk_debate_state.get(HISTORYS.safe_history, ""),
            HISTORYS.neutral_history: risk_debate_state.get(HISTORYS.neutral_history, ""),
            HISTORYS.expected_history: risk_debate_state.get(HISTORYS.expected_history, ""),
            STATE.latest_speaker: SPEAKERS.aggressive,
            RESPONSES.aggressive: argument,
            RESPONSES.neutral: risk_debate_state.get(RESPONSES.neutral, ""),
            RESPONSES.safe: risk_debate_state.get(RESPONSES.safe, ""),
            RESPONSES.expected: risk_debate_state.get(RESPONSES.expected, ""),
            STATE.count: risk_debate_state.get(STATE.count, 0) + 1,
        }

        return {STATE.risk_debate_state: new_risk_debate_state}

    return aggressive_node
