from tennisAgents.utils.enumerations import *

def create_neutral_debator(llm):
    def neutral_node(state) -> dict:
        risk_debate_state = state[STATE.risk_debate_state]
        history = risk_debate_state.get(HISTORYS.history, "")
        neutral_history = risk_debate_state.get(HISTORYS.neutral_history, "")

        current_aggressive_response = risk_debate_state.get(RESPONSES.aggressive, "")
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
Como analista de riesgo neutral, tu función es ofrecer una perspectiva equilibrada sobre la propuesta del Trader, considerando tanto las oportunidades como los riesgos de forma objetiva.

Tu objetivo es **evaluar de forma crítica las posturas del analista conservador y del agresivo**, destacando sus puntos fuertes y débiles, para construir una estrategia moderada que combine potencial de éxito y control del riesgo.

Usa la siguiente información:
- Informe meteorológico: {weather_report}
- Cuotas de apuestas: {odds_report}
- Sentimiento en redes sociales: {sentiment_report}
- Noticias recientes: {news_report}
- Estado físico/mental de jugadores: {players_report}
- Información del torneo: {tournament_report}

Últimos argumentos:
- Analista agresivo: {current_aggressive_response}
- Analista seguro: {current_safe_response}
- Analista de probabilidades: {current_expected_response}

Historial de debate: {history}

Tu respuesta debe:
- Rebatir ideas extremas (riesgo excesivo o prudencia extrema)
- Proponer un enfoque equilibrado y justificado
- Ser conversacional, directa y sin formato especial

No inventes respuestas si faltan voces en el debate. Céntrate en el análisis comparativo y busca un equilibrio racional en las apuestas.
"""

        response = llm.invoke(prompt)

        argument = f"Neutral Analyst: {response.content}"

        new_risk_debate_state = {
            HISTORYS.history: history + "\n" + argument,
            HISTORYS.aggressive_history: risk_debate_state.get(HISTORYS.aggressive_history, ""),
            HISTORYS.safe_history: risk_debate_state.get(HISTORYS.safe_history, ""),
            HISTORYS.neutral_history: neutral_history + "\n" + argument,
            HISTORYS.expected_history: risk_debate_state.get(HISTORYS.expected_history, ""),
            STATE.latest_speaker: SPEAKERS.neutral,
            RESPONSES.aggressive: risk_debate_state.get(RESPONSES.aggressive, ""),
            RESPONSES.safe: risk_debate_state.get(RESPONSES.safe, ""),
            RESPONSES.neutral: argument,
            RESPONSES.expected: risk_debate_state.get(RESPONSES.expected, ""),
            STATE.count: risk_debate_state.get(STATE.count, 0) + 1,
        }

        return {STATE.risk_debate_state: new_risk_debate_state}

    return neutral_node
