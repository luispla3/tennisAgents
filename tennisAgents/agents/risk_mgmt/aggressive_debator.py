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
Como analista de riesgo agresivo, tu misión es defender estrategias de alta recompensa, incluso si implican riesgos significativos. Estás evaluando la propuesta del Trader y tu tarea es **respaldarla o incluso sugerir apuestas más audaces**, siempre que estén justificadas.

**INFORMACIÓN DEL USUARIO Y PARTIDO:**
- Saldo disponible: ${wallet_balance}
- Fecha del partido: {match_date}
- Jugador de interés: {player_of_interest}
- Oponente: {opponent}
- Torneo: {tournament}
- Superficie: {surface}
- Ubicación: {location}

**TU TAREA PRINCIPAL:**
Basándote en la información de los analistas, debes decidir cuánto dinero invertir en cada uno de los siguientes tipos de apuestas, usando técnicas matemáticas y probabilísticas:

1. **CUOTAS DE PARTIDO**: Decidir cuál de ambos jugadores gana el partido
2. **APUESTAS A SETS**: Si no es Grand Slam (mejor de 3 sets), decidir:
   - Jugador A 2-0, Jugador A 2-1, Jugador B 2-0, Jugador B 2-1
3. **GANADOR DEL ACTUAL SET**: Si se está jugando el primer set, decidir quién lo gana
4. **RESULTADO DEL ACTUAL SET**: Si se está jugando el segundo set, decidir quién lo gana y el resultado (6-0, 6-1, 6-2, 6-3, 6-4, 7-5)
5. **JUGADOR GANA AL MENOS UN SET**: Jugador A SI/NO, Jugador B SI/NO
6. **PARTIDO Y AMBOS JUGADORES GANAN UN SET**: Jugador A gana partido + ambos ganan set, o Jugador B gana partido + ambos ganan set

**INFORMES DISPONIBLES:**
- Pronóstico del tiempo: {weather_report}
- Informe de cuotas de apuestas: {odds_report}
- Sentimiento en redes sociales: {sentiment_report}
- Noticias recientes: {news_report}
- Estado físico y mental de los jugadores: {players_report}
- Información del torneo: {tournament_report}
- Estado del partido en vivo: {match_live_report}

**ARGUMENTOS PREVIOS:**
- Analista conservadora: {current_safe_response}
- Analista neutral: {current_neutral_response}
- Analista de probabilidades: {current_expected_response}

**HISTORIAL DE DEBATE:**
{history}

**REQUISITOS DE TU RESPUESTA:**
1. **EXPLICA** tu estrategia de inversión agresiva para cada tipo de apuesta
2. **CALCULA** el porcentaje del saldo a invertir en cada apuesta usando análisis probabilístico
3. **JUSTIFICA** matemáticamente por qué tomar riesgos tiene sentido dadas las circunstancias
4. **REBATE** directamente los argumentos de los analistas conservador y neutral
5. **USA** técnicas matemáticas y probabilísticas para predecir correctamente cómo se reparte el dinero
6. **DEMUESTRA** que la estrategia de riesgo es la más lógica dadas las circunstancias

Tu respuesta debe ser conversacional, directa, sin formato especial. No inventes si no hay respuestas previas. ¡Debes persuadir con datos y análisis matemático!
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
