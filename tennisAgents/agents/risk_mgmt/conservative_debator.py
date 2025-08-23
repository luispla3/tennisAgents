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
Como Analista Conservador de Riesgos, tu principal objetivo es **minimizar el riesgo**, proteger los fondos disponibles y evitar apuestas excesivamente arriesgadas. Debes evaluar la propuesta del Trader y argumentar por qué podría ser imprudente o arriesgada en función del contexto actual.

**INFORMACIÓN DEL USUARIO Y PARTIDO:**
- Saldo disponible: ${wallet_balance}
- Fecha del partido: {match_date}
- Jugador de interés: {player_of_interest}
- Oponente: {opponent}
- Torneo: {tournament}
- Superficie: {surface}
- Ubicación: {location}

**TU TAREA PRINCIPAL:**
Basándote en la información de los analistas, debes decidir cuánto dinero invertir en cada uno de los siguientes tipos de apuestas, usando técnicas matemáticas y probabilísticas, pero con un enfoque CONSERVADOR:

1. **CUOTAS DE PARTIDO**: Decidir cuál de ambos jugadores gana el partido (apuesta más segura)
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
- Analista neutral: {current_neutral_response}
- Analista de probabilidades: {current_expected_response}

**HISTORIAL DE DEBATE:** {history}

**REQUISITOS DE TU RESPUESTA:**
1. **ANALIZA** las propuestas de los otros analistas y muestra sus riesgos matemáticamente
2. **CALCULA** el porcentaje del saldo a invertir en cada apuesta usando análisis probabilístico CONSERVADOR
3. **PROPON** una versión más segura o incluso abstenerse de apostar en ciertos casos
4. **USA** técnicas matemáticas y probabilísticas para demostrar por qué el enfoque conservador es mejor
5. **REBATE** las posturas del analista agresivo y del neutral, señalando los puntos ciegos
6. **DEMUESTRA** que una estrategia conservadora protege mejor los intereses a largo plazo

Tu respuesta debe:
- Ser conversacional y natural sin formato especial
- No inventar respuestas si no hay datos disponibles
- Mostrar por qué una estrategia conservadora es matemáticamente superior en escenarios inciertos
- Usar análisis probabilístico para justificar la distribución conservadora del dinero
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
