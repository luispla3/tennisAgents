from tennisAgents.utils.enumerations import *

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

        prompt = f"""
Como analista de riesgo agresivo, tu misión es defender estrategias de alta recompensa, incluso si implican riesgos significativos. Estás evaluando la propuesta del Trader y tu tarea es **respaldarla o incluso sugerir apuestas más audaces**, siempre que estén justificadas.

Debes utilizar los siguientes informes:
- Pronóstico del tiempo: {weather_report}
- Informe de cuotas de apuestas: {odds_report}
- Sentimiento en redes sociales: {sentiment_report}
- Noticias recientes: {news_report}
- Estado físico y mental de los jugadores: {players_report}
- Información del torneo: {tournament_report}

Argumenta por qué tomar riesgos tiene sentido. **Rebate directamente** los argumentos de los analistas conservador y neutral si están disponibles:
- Analista conservadora: {current_safe_response}
- Analista neutral: {current_neutral_response}
- Analista de probabilidades: {current_expected_response}

Historial de debate:
{history}

Tu respuesta debe ser conversacional, directa, sin formato especial. No inventes si no hay respuestas previas. Concéntrate en demostrar que la estrategia de riesgo **es la más lógica dadas las circunstancias**. No te limites a repetir datos, ¡debes persuadir!
"""

        response = llm.invoke(prompt)

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
