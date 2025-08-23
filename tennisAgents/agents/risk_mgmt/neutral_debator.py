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
Como analista de riesgo neutral, tu función es ofrecer una perspectiva equilibrada sobre la propuesta del Trader, considerando tanto las oportunidades como los riesgos de forma objetiva.

**INFORMACIÓN DEL USUARIO Y PARTIDO:**
- Saldo disponible: ${wallet_balance}
- Fecha del partido: {match_date}
- Jugador de interés: {player_of_interest}
- Oponente: {opponent}
- Torneo: {tournament}
- Superficie: {surface}
- Ubicación: {location}

**TU TAREA PRINCIPAL:**
Basándote en la información de los analistas, debes decidir cuánto dinero invertir en cada uno de los siguientes tipos de apuestas, usando técnicas matemáticas y probabilísticas, pero con un enfoque EQUILIBRADO:

1. **CUOTAS DE PARTIDO**: Decidir cuál de ambos jugadores gana el partido
2. **APUESTAS A SETS**: Si no es Grand Slam (mejor de 3 sets), decidir:
   - Jugador A 2-0, Jugador A 2-1, Jugador B 2-0, Jugador B 2-1
3. **GANADOR DEL ACTUAL SET**: Si se está jugando el primer set, decidir quién lo gana
4. **RESULTADO DEL ACTUAL SET**: Si se está jugando el segundo set, decidir quién lo gana y el resultado (6-0, 6-1, 6-2, 6-3, 6-4, 7-5)
5. **JUGADOR GANA AL MENOS UN SET**: Jugador A SI/NO, Jugador B SI/NO
6. **PARTIDO Y AMBOS JUGADORES GANAN UN SET**: Jugador A gana partido + ambos ganan set, o Jugador B gana partido + ambos ganan set

**INFORMES DISPONIBLES:**
- Informe meteorológico: {weather_report}
- Cuotas de apuestas: {odds_report}
- Sentimiento en redes sociales: {sentiment_report}
- Noticias recientes: {news_report}
- Estado físico/mental de jugadores: {players_report}
- Información del torneo: {tournament_report}
- Estado del partido en vivo: {match_live_report}

**ARGUMENTOS PREVIOS:**
- Analista agresivo: {current_aggressive_response}
- Analista seguro: {current_safe_response}
- Analista de probabilidades: {current_expected_response}

**HISTORIAL DE DEBATE:** {history}

**REQUISITOS DE TU RESPUESTA:**
1. **EVALÚA** de forma crítica las posturas del analista conservador y del agresivo
2. **CALCULA** el porcentaje del saldo a invertir en cada apuesta usando análisis probabilístico EQUILIBRADO
3. **DESTACA** los puntos fuertes y débiles de cada postura
4. **CONSTRUYE** una estrategia moderada que combine potencial de éxito y control del riesgo
5. **USA** técnicas matemáticas y probabilísticas para justificar el enfoque equilibrado
6. **REBATE** ideas extremas (riesgo excesivo o prudencia extrema)

Tu respuesta debe:
- Ser conversacional, directa y sin formato especial
- No inventar respuestas si faltan voces en el debate
- Céntrate en el análisis comparativo y busca un equilibrio racional en las apuestas
- Usar análisis probabilístico para demostrar por qué el enfoque equilibrado es matemáticamente superior
- Mostrar cómo combinar lo mejor de ambas estrategias (agresiva y conservadora)
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
