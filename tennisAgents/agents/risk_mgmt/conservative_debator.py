from tennisAgents.utils.enumerations import *

def create_conservative_debator(llm):
    def conservative_node(state) -> dict:
        risk_debate_state = state[STATE.risk_debate_state]
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
Como analista de riesgo conservadora, tu misión es defender estrategias de baja volatilidad y alta probabilidad, que son las que se esperan que sucedan siguiendo la previsión del marcador actual.

**INFORMACIÓN DEL USUARIO Y PARTIDO:**
- Fecha del partido: {match_date}
- Jugador de interés: {player_of_interest}
- Oponente: {opponent}
- Torneo: {tournament}
- Superficie: {surface}
- Ubicación: {location}

**TU TAREA PRINCIPAL:**
Basándote en la información de los reportes de los analistas, y en los 4 fundamentales que se han analizado, nunca haciendo 2 inversiones del mismo tipo de apuesta, usando técnicas matemáticas y probabilísticas, deberás hacer lo siguiente:

1. **4 FUNDAMENTALES**: Valorar y revisar los 4 fundamentales que se encuentran en los reportes de los analistas, desde una visión completa de lo analizado, siendo además un poco más conservadora en la valoración de los fundamentales.
2. **RESULTADO DEL SET**: Decidir cuál de ambos jugadores gana el set, y el resultado del set (6-0, 6-1, 6-2, 6-3, 6-4, 7-5, 7-6)

**INFORMES DISPONIBLES:**
- Pronóstico del tiempo: {weather_report}
- Informe de cuotas de apuestas: {odds_report}
- Sentimiento en redes sociales: {sentiment_report}
- Noticias recientes: {news_report}
- Estado físico y mental de los jugadores: {players_report}
- Información del torneo: {tournament_report}
- Estado del partido en vivo: {match_live_report}

**ARGUMENTOS PREVIOS:**
- Analista agresivo: {current_aggressive_response}
- Analista neutral: {current_neutral_response}
- Analista de probabilidades: {current_expected_response}

**HISTORIAL DE DEBATE:**
{history}

**REQUISITOS DE TU RESPUESTA:**
1. **GENERA** los 4 fundamentals desde tu vision comentada anteriormente.
   IMPORTANTE: Cuando comentes sobre cada fundamental, DEBES incluir expresamente el encabezado:
   - "FUNDAMENTAL 1: ANÁLISIS DE CONSISTENCIA DEL FAVORITO"
   - "FUNDAMENTAL 2: ANÁLISIS CRÍTICO DEL SERVICIO EN LA SUPERFICIE"
   - "FUNDAMENTAL 3: PREDICCIÓN DEL RESULTADO DEL SET"
   - "FUNDAMENTAL 4: ANÁLISIS DEL SERVICIO Y PROBABILIDAD DE MANTENER EL SAQUE"
2. **EXPLICA** tu estrategia de inversión conservadora para el resultado del set
3. **JUSTIFICA** matemáticamente por qué minimizar el riesgo tiene sentido dadas las circunstancias
4. **REBATE** directamente los argumentos de los analistas agresivo y neutral
5. **DEMUESTRA** que la estrategia conservadora es la más lógica dadas las circunstancias

Tu respuesta debe ser conversacional, directa, sin formato especial. No inventes si no hay respuestas previas. ¡Debes persuadir con datos y análisis matemático!
"""

        response = llm.invoke(prompt)

        argument = f"Safe Analyst: {response.content}"

        new_risk_debate_state = {
            HISTORYS.history: history + "\n" + argument,
            HISTORYS.aggressive_history: risk_debate_state.get(HISTORYS.aggressive_history, ""),
            HISTORYS.safe_history: safe_history + "\n" + argument,
            HISTORYS.neutral_history: risk_debate_state.get(HISTORYS.neutral_history, ""),
            HISTORYS.expected_history: risk_debate_state.get(HISTORYS.expected_history, ""),
            STATE.latest_speaker: SPEAKERS.safe,
            RESPONSES.aggressive: risk_debate_state.get(RESPONSES.aggressive, ""),
            RESPONSES.safe: argument,
            RESPONSES.neutral: risk_debate_state.get(RESPONSES.neutral, ""),
            RESPONSES.expected: risk_debate_state.get(RESPONSES.expected, ""),
            STATE.count: risk_debate_state.get(STATE.count, 0) + 1,
        }

        return {STATE.risk_debate_state: new_risk_debate_state}

    return conservative_node
