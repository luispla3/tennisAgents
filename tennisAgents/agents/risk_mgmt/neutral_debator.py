def create_neutral_debator(llm):
    def neutral_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        neutral_history = risk_debate_state.get("neutral_history", "")

        current_aggressive_response = risk_debate_state.get("current_aggressive_response", "")
        current_conservative_response = risk_debate_state.get("current_conservative_response", "")

        trader_plan = state["trader_plan"]

        # Informes disponibles
        weather_report = state["weather_report"]
        odds_report = state["odds_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        tournament_report = state["tournament_report"]

        prompt = f"""
Como analista de riesgo neutral, tu función es ofrecer una perspectiva equilibrada sobre la propuesta del Trader, considerando tanto las oportunidades como los riesgos de forma objetiva.

Tu objetivo es **evaluar de forma crítica las posturas del analista conservador y del agresivo**, destacando sus puntos fuertes y débiles, para construir una estrategia moderada que combine potencial de éxito y control del riesgo.

Usa la siguiente información:
- Informe meteorológico: {weather_report}
- Cuotas de apuestas: {odds_report}
- Sentimiento en redes sociales: {sentiment_report}
- Noticias recientes: {news_report}
- Estado físico/mental de jugadores: {fundamentals_report}
- Información del torneo: {tournament_report}

Últimos argumentos:
- Trader: {trader_plan}
- Analista agresivo: {current_aggressive_response}
- Analista conservador: {current_conservative_response}

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
            "history": history + "\n" + argument,
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": neutral_history + "\n" + argument,
            "latest_speaker": "Neutral",
            "current_aggressive_response": current_aggressive_response,
            "current_conservative_response": current_conservative_response,
            "current_neutral_response": argument,
            "count": risk_debate_state.get("count", 0) + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return neutral_node
