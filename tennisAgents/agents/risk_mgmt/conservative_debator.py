def create_conservative_debator(llm):
    def conservative_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        safe_history = risk_debate_state.get("safe_history", "")

        current_aggressive_response = risk_debate_state.get("current_aggressive_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")
        current_expected_response = risk_debate_state.get("current_expected_response", "")

        # Informes disponibles
        news_report = state["news_report"]
        odds_report = state["odds_report"]
        players_report = state["players_report"]        
        sentiment_report = state["sentiment_report"]
        tournament_report = state["tournament_report"]
        weather_report = state["weather_report"]
        

        prompt = f"""
Como Analista Conservador de Riesgos, tu principal objetivo es **minimizar el riesgo**, proteger los fondos disponibles y evitar apuestas excesivamente arriesgadas. Debes evaluar la propuesta del Trader y argumentar por qué podría ser imprudente o arriesgada en función del contexto actual.

Tu misión es **rebatir las posturas del analista agresivo y del neutral**, señalando los puntos ciegos, sobreestimaciones o posibles riesgos que ellos podrían no haber considerado.

Tu respuesta debe apoyarse en los siguientes informes:
- Informe meteorológico: {weather_report}
- Cuotas de apuestas: {odds_report}
- Sentimiento en redes sociales: {sentiment_report}
- Noticias recientes: {news_report}
- Estado físico/mental de jugadores: {players_report}
- Información del torneo: {tournament_report}

Últimos argumentos:
- Analista agresivo: {current_aggressive_response}
- Analista neutral: {current_neutral_response}
- Analista de probabilidades: {current_expected_response}

Historial de debate: {history}

Debes:
- Analizar sus propuestas y mostrar sus riesgos
- Proponer una versión más segura o incluso abstenerse de apostar
- Hablar de forma natural (conversacional) sin formato especial
- No inventes respuestas si no hay datos disponibles

Muestra por qué una estrategia conservadora protege mejor los intereses a largo plazo frente a escenarios inciertos.
"""

        response = llm.invoke(prompt)

        argument = f"Safe Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "safe_history": safe_history + "\n" + argument,
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "expected_history": risk_debate_state.get("expected_history", ""),
            "latest_speaker": "Safe",
            "current_aggressive_response": risk_debate_state.get("current_aggressive_response", ""),
            "current_safe_response": argument,
            "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
            "current_expected_response": risk_debate_state.get("current_expected_response", ""),
            "count": risk_debate_state.get("count", 0) + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return conservative_node
