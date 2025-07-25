def create_expected_debator(llm):
    def expected_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        expected_history = risk_debate_state.get("expected_history", "")

        current_aggressive_response = risk_debate_state.get("current_aggressive_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")
        current_safe_response = risk_debate_state.get("current_safe_response", "")

        # Informes disponibles
        weather_report = state["weather_report"]
        odds_report = state["odds_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        tournament_report = state["tournament_report"]

        prompt = f"""
Como Analista de Valor Esperado, tu papel es **evaluar racionalmente si la propuesta de apuesta del Trader es rentable** a largo plazo, teniendo en cuenta la **probabilidad implícita** en las cuotas y la calidad de la información disponible.

Tu tarea es calcular o estimar (de forma razonada, no matemática exacta) si el valor esperado (Expected Value, EV) es positivo o negativo, en función de:
- Cuotas de apuestas ({odds_report})
- Condiciones del jugador (estado físico, forma reciente, motivación, etc.): {fundamentals_report}
- Influencias externas (torneo, condiciones meteorológicas, presión mediática...): {tournament_report}, {weather_report}, {news_report}
- Sentimiento del público o la comunidad: {sentiment_report}

Últimos argumentos de los analistas:
- Agresivo: {current_aggressive_response}
- Neutral: {current_neutral_response}
- Conservador: {current_safe_response}

Historial de debate: {history}

Tu respuesta debe:
- Calcular si el riesgo merece la pena según el valor esperado
- Cuestionar los argumentos de los demás desde una visión probabilística
- Reforzar (o criticar) el plan del Trader si el valor esperado lo justifica
- Ser conversacional (sin formato especial)
- No inventes información si falta; puedes decir que faltan datos para calcular el valor esperado con seguridad

Apunta a responder si es **matemáticamente rentable o no**, más allá de opiniones subjetivas.
"""

        response = llm.invoke(prompt)

        argument = f"Expected Value Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "expected_history": expected_history + "\n" + argument,
            "latest_speaker": "Expected",
            "current_aggressive_response": risk_debate_state.get("current_aggressive_response", ""),
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
            "current_expected_response": argument,
            "count": risk_debate_state.get("count", 0) + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return expected_node
