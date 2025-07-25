from tennisAgents.utils.enumerations import *

def create_conservative_debator(llm):
    def conservative_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get(HISTORYS.history, "")
        safe_history = risk_debate_state.get(HISTORYS.safe_history, "")

        current_aggressive_response = risk_debate_state.get(RESPONSES.aggressive, "")
        current_neutral_response = risk_debate_state.get(RESPONSES.neutral, "")
        current_expected_response = risk_debate_state.get(RESPONSES.expected, "")

        # Informes disponibles
        news_report = state[REPORTS.news_report]
        odds_report = state[REPORTS.odds_report]
        players_report = state[REPORTS.players_report]
        sentiment_report = state[REPORTS.sentiment_report]
        tournament_report = state[REPORTS.tournament_report]
        weather_report = state[REPORTS.weather_report]


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
            HISTORYS.history: history + "\n" + argument,
            HISTORYS.aggressive_history: risk_debate_state.get(HISTORYS.aggressive_history, ""),
            HISTORYS.safe_history: safe_history + "\n" + argument,
            HISTORYS.neutral_history: risk_debate_state.get(HISTORYS.neutral_history, ""),
            HISTORYS.expected_history: risk_debate_state.get(HISTORYS.expected_history, ""),
            "latest_speaker": SPEAKERS.safe,
            RESPONSES.aggressive: risk_debate_state.get(RESPONSES.aggressive, ""),
            RESPONSES.safe: argument,
            RESPONSES.neutral: risk_debate_state.get(RESPONSES.neutral, ""),
            RESPONSES.expected: risk_debate_state.get(RESPONSES.expected, ""),
            "count": risk_debate_state.get("count", 0) + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return conservative_node
