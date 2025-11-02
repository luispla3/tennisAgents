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
Como analista de riesgo neutral (pero realista), tu misión es buscar un equilibrio entre la perspectiva más probable de acertar y las oportunidades de inversión innovadoras, balanceando seguridad y potencial de rentabilidad.

**INFORMACIÓN DEL USUARIO Y PARTIDO:**
- Fecha del partido: {match_date}
- Jugador de interés: {player_of_interest}
- Oponente: {opponent}
- Torneo: {tournament}
- Superficie: {surface}
- Ubicación: {location}
- Saldo disponible: ${wallet_balance}

**TU TAREA PRINCIPAL:**
Basándote en la información de los reportes de los analistas, en las cuotas de apuestas disponibles, y en los 4 fundamentales que se han analizado, nunca haciendo 2 inversiones contrarias de apuesta, usando técnicas matemáticas y probabilísticas, deberás hacer lo siguiente:

1. **4 FUNDAMENTALES**: Valorar y validar los 4 fundamentales que se encuentran en los reportes de los analistas, desde una visión completa basada en la información de los reportes de los analistas, equilibrando tanto la perspectiva más probable como las oportunidades de inversión.
2. **RESULTADO DEL SET**: Decidir cuál de ambos jugadores gana el set, y el resultado del set (6-0, 6-1, 6-2, 6-3, 6-4, 7-5, 7-6) balanceando probabilidad y valor.
3. **CUOTAS DE APUESTAS**: Estudiar las cuotas de apuestas disponibles.
4. **CONTRASTE ENTRE FUNDAMENTALES Y CUOTAS DE APUESTAS**: Estudiar si las cuotas de apuestas son coherentes con los fundamentales. Analizar tanto si la opción más probable está bien reflejada, como si hay oportunidades moderadas de inversión con buen balance riesgo-beneficio.
5. **ESTRATEGIA DE INVERSIÓN**: Dispones del saldo disponible ${wallet_balance} para invertir. Genera una estrategia de inversión basada en los fundamentales y las cuotas de apuestas, que equilibre inversiones seguras y probables con oportunidades moderadamente arriesgadas pero con buen valor. Si se considera que no hay ninguna oportunidad de inversión con buen equilibrio, decir que no hay ninguna oportunidad de inversión y por tanto no se apuesta. Buscamos un equilibrio entre probabilidad de éxito y rentabilidad potencial.

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
- Analista agresivo: {current_aggressive_response}
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
2. **EXPLICA** tu estrategia de inversión equilibrada para el resultado del set y las cuotas de apuestas, balanceando probabilidad y valor.
3. **JUSTIFICA** matemáticamente por qué el enfoque equilibrado tiene sentido dadas las circunstancias
4. **REBATE** directamente los argumentos de los analistas agresivo y conservador
5. **DEMUESTRA** que la estrategia equilibrada (balance entre probabilidad y oportunidades) para el resultado del set y las cuotas de apuestas es la más lógica dadas las circunstancias.

Tu respuesta debe ser conversacional, directa, sin formato especial. No inventes si no hay respuestas previas. ¡Debes persuadir con datos y análisis matemático!
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
