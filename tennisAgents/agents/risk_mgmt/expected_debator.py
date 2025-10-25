from tennisAgents.utils.enumerations import *

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
        surface = state.get(STATE.surface, "")
        location = state.get(STATE.location, "")

        prompt = f"""
Como Analista de Valor Esperado, tu función es **evaluar y relacionar las cuotas de las odds disponibles** analizando la probabilidad implicita y si la probabilidad real supera el umbral de rentabilidad.

**INFORMACION DEL PARTIDO:**
- Jugador: {player_of_interest} vs {opponent}
- Torneo: {tournament} | Superficie: {surface} | Ubicación: {location}
- Fecha: {match_date} | Saldo: ${wallet_balance}

**TU ANÁLISIS:**
Para cada odd disponible en {odds_report}, determina:
- **Probabilidad implícita**: Si la odd es *10, la casa de apuestas implica 10% de probabilidad (1/10).
- **Probabilidad real estimada**: Basándote en {players_report}, {tournament_report}, {weather_report}, {news_report}, {sentiment_report}, {match_live_report}, ¿la probabilidad REAL es mayor?
- **Criterio de rentabilidad**: Para odd *X, necesitas ganar más de 1 de cada X veces. Ejemplo: odd *10 → ¿probabilidad real > 10%?
Concluye que informacion sugieren estas odds y cómo repercute en el resultado del set.

Informate de los últimos argumentos de los analistas, y debatelos desde con esta información que has tenido:
- Analista Agresivo: {current_aggressive_response}
- Analista Neutral: {current_neutral_response}
- Analista Seguro: {current_safe_response}

Historial: {history}

**Responde de forma conversacional:**
1. Analiza y relacionalas odds disponibles y compara probabilidades implícitas vs reales
2. Identifica cuál odd (si alguna) tiene valor esperado positivo y si la probabilidad real supera el umbral de rentabilidad.
3. Si encuentras valor positivo, sugiere % del saldo (Kelly fraccional 0.25-0.5); si no, sugiere 0%
4. Cuestiona argumentos con visión probabilística, siendo conversacional (sin formato especial)

No inventes datos. Se directo sobre rentabilidad matemática a largo plazo.
"""

        response = llm.invoke(prompt)

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
