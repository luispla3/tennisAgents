def create_aggressive_debator(llm):
    def aggressive_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        aggressive_history = risk_debate_state.get("aggressive_history", "")

        current_neutral_response = risk_debate_state.get("current_neutral_response", "")
        current_safe_response = risk_debate_state.get("current_safe_response", "")
        current_expected_response = risk_debate_state.get("current_expected_response", "")

        # Informes disponibles
        news_report = state["news_report"]
        odds_report = state["odds_report"]
        players_report = state["players_report"]        
        sentiment_report = state["sentiment_report"]
        tournament_report = state["tournament_report"]
        weather_report = state["weather_report"]

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
            "history": history + "\n" + argument,
            "aggressive_history": aggressive_history + "\n" + argument,
            "safe_history": risk_debate_state.get("safe_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "expected_history": risk_debate_state.get("expected_history", ""),
            "latest_speaker": "Aggressive",
            "current_aggressive_response": argument,
            "current_safe_response": current_safe_response,
            "current_neutral_response": current_neutral_response,
            "current_expected_response": current_expected_response,
            "count": risk_debate_state.get("count", 0) + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return aggressive_node
