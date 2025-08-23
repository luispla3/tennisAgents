from tennisAgents.utils.enumerations import *

def create_risk_manager(llm, memory):
    def risk_manager_node(state) -> dict:
        risk_debate_state = state[STATE.risk_debate_state]
        history = risk_debate_state[HISTORYS.history]

        # Informes previos disponibles
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

        # Memorias de errores pasados
        curr_situation = f"{weather_report}\n\n{odds_report}\n\n{sentiment_report}\n\n{news_report}\n\n{players_report}\n\n{tournament_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""
Como Juez de Riesgos en un sistema de apuestas deportivas, tu objetivo es evaluar el debate entre **cuatro analistas** (Agresivo, Conservador, Neutral y Basado en Valor Esperado) y generar un INFORME FINAL ESTRUCTURADO y CLARO sobre la decisión de apuesta.

**INFORMACIÓN DEL PARTIDO:**
- Saldo disponible: ${wallet_balance}
- Fecha: {match_date}
- Jugador de interés: {player_of_interest}
- Oponente: {opponent}
- Torneo: {tournament}
- Superficie: {surface}
- Ubicación: {location}

### TU TAREA:
Analiza el debate entre los analistas y genera un INFORME FINAL que incluya:

1. **DECISIÓN PRINCIPAL**: ¿APOSTAR o NO APOSTAR?
2. **JUGADOR FAVORITO**: Si se apuesta, ¿a favor de quién?
3. **DISTRIBUCIÓN DEL DINERO**: Cómo se reparte el dinero entre los 6 tipos de apuestas
4. **JUSTIFICACIÓN COMPLETA**: Por qué se toma esta decisión

### TIPOS DE APUESTAS A CONSIDERAR:
1. **Cuotas de Partido** - Quién gana el partido
2. **Apuestas a Sets** - Resultado en sets (2-0, 2-1, etc.)
3. **Ganador del Actual Set** - Quién gana el set en curso
4. **Resultado del Actual Set** - Score específico (6-0, 6-1, etc.)
5. **Jugador Gana al Menos un Set** - SI/NO para cada jugador
6. **Partido y Ambos Ganan un Set** - Combinación ganador + ambos ganan set

### Debate actual entre analistas:
{history}

### Lecciones aprendidas de situaciones similares:
{past_memory_str}

### FORMATO DEL INFORME FINAL:
Tu respuesta debe seguir EXACTAMENTE esta estructura:

**DECISIÓN FINAL: [APOSTAR/NO APOSTAR]**

**JUGADOR FAVORITO: [Nombre del jugador o N/A si no se apuesta]**

**DISTRIBUCIÓN DEL DINERO:**
- Cuotas de Partido: $[cantidad] ([porcentaje]%)
- Apuestas a Sets: $[cantidad] ([porcentaje]%)
- Ganador del Actual Set: $[cantidad] ([porcentaje]%)
- Resultado del Actual Set: $[cantidad] ([porcentaje]%)
- Jugador Gana al Menos un Set: $[cantidad] ([porcentaje]%)
- Partido y Ambos Ganan un Set: $[cantidad] ([porcentaje]%)

**JUSTIFICACIÓN:**
[Explicación detallada de por qué se toma esta decisión, basándose en el análisis de los debators y los informes disponibles]

**NIVEL DE CONFIANZA: [ALTO/MEDIO/BAJO]**

**RECOMENDACIONES ADICIONALES:**
[Consejos sobre cuándo ejecutar las apuestas, qué monitorear, etc.]

IMPORTANTE: Usa análisis matemático y probabilístico para justificar la distribución del dinero. No inventes información, usa solo los datos disponibles en el debate y los informes.
"""

        response = llm.invoke(prompt)

        new_risk_debate_state = {
            STATE.judge_decision: response.content,
            HISTORYS.history: history,
            HISTORYS.aggressive_history: risk_debate_state.get(HISTORYS.aggressive_history, ""),
            HISTORYS.safe_history: risk_debate_state.get(HISTORYS.safe_history, ""),
            HISTORYS.neutral_history: risk_debate_state.get(HISTORYS.neutral_history, ""),
            HISTORYS.expected_history: risk_debate_state.get(HISTORYS.expected_history, ""),
            STATE.latest_speaker: SPEAKERS.judge,
            RESPONSES.aggressive: risk_debate_state.get(RESPONSES.aggressive, ""),
            RESPONSES.safe: risk_debate_state.get(RESPONSES.safe, ""),
            RESPONSES.neutral: risk_debate_state.get(RESPONSES.neutral, ""),
            RESPONSES.expected: risk_debate_state.get(RESPONSES.expected, ""),
            STATE.count: risk_debate_state[STATE.count],
        }

        return {
            STATE.risk_debate_state: new_risk_debate_state,
            STATE.final_bet_decision: response.content,
        }

    return risk_manager_node
