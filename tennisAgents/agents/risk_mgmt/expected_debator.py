from tennisAgents.utils.enumerations import *

def create_expected_debator(llm):
    def expected_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
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

        prompt = f"""
Como Analista de Valor Esperado, tu papel es **evaluar racionalmente si la propuesta de apuesta del Trader es rentable** a largo plazo, teniendo en cuenta la **probabilidad implícita** en las cuotas y la calidad de la información disponible.

Tu tarea es calcular o estimar (de forma razonada, no matemática exacta) si el valor esperado (Expected Value, EV) es positivo o negativo, en función de:
- Cuotas de apuestas ({odds_report})
- Condiciones del jugador (estado físico, forma reciente, motivación, etc.): {players_report}
- Influencias externas (torneo, condiciones meteorológicas, presión mediática...): {tournament_report}, {weather_report}, {news_report}
- Sentimiento del público o la comunidad: {sentiment_report}

Últimos argumentos de los analistas:
- Analista Agresivo: {current_aggressive_response}
- Analista Neutral: {current_neutral_response}
- Analista Seguro: {current_safe_response}

Historial de debate: {history}

Tu respuesta debe:
- Calcular si el riesgo merece la pena según el valor esperado
- Cuestionar los argumentos de los demás desde una visión probabilística
- Ser conversacional (sin formato especial)
- No inventes información si falta; puedes decir que faltan datos para calcular el valor esperado con seguridad

Apunta a responder si es **matemáticamente rentable o no**, más allá de opiniones subjetivas.
"""

        response = llm.invoke(prompt)

        argument = f"Expected Value Analyst: {response.content}"

        new_risk_debate_state = {
            HISTORYS.history: history + "\n" + argument,
            HISTORYS.aggressive_history: risk_debate_state.get(HISTORYS.aggressive_history, ""),
            HISTORYS.safe_history: risk_debate_state.get(HISTORYS.safe_history, ""),
            HISTORYS.neutral_history: risk_debate_state.get(HISTORYS.neutral_history, ""),
            HISTORYS.expected_history: expected_history + "\n" + argument,
            "latest_speaker": SPEAKERS.expected,
            RESPONSES.aggressive: risk_debate_state.get(RESPONSES.aggressive, ""),
            RESPONSES.safe: risk_debate_state.get(RESPONSES.safe, ""),
            RESPONSES.neutral: risk_debate_state.get(RESPONSES.neutral, ""),
            RESPONSES.expected: argument,
            "count": risk_debate_state.get("count", 0) + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return expected_node
