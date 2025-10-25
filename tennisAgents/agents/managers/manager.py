
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
Decide con qué vision de los 4 fundamentals generada por cada debator te vas a quedar, y comparala matematicamente con cada uno de los casos ideales. Si el resultado matematico de alguna de las comparaciones es alto, se da por válida la vision adoptada , y se tomará la decision y justificacion dada en la vision adoptada (no en el caso ideal).
Finalmente, genera un INFORME FINAL que incluya:

1. **DECISIÓN PRINCIPAL**: ¿APOSTAR o NO APOSTAR?
2. **JUGADOR FAVORITO**: Si se apuesta, ¿a favor de quién?
3. **DISTRIBUCIÓN DEL DINERO**: Qué apuesta se hace y cuanto se apuesta (Cantidad a apostar = 1 euro o nada, siempre)
4. **JUSTIFICACIÓN COMPLETA**: Por qué se toma esta decisión

### TIPO DE APUESTA A CONSIDERAR:
1. **Cuotas de Resultado del Primer Set** - Quien gana el primer set y el resultado del set (6-0, 6-1, 6-2, 6-3, 6-4, 7-5, 7-6)

### Debate actual entre analistas:
{history}

### Lecciones aprendidas de situaciones similares:
{past_memory_str}

### FORMATO DEL INFORME FINAL:
Tu respuesta debe seguir EXACTAMENTE esta estructura:

**DECISIÓN FINAL: [APOSTAR/NO APOSTAR]**

**JUGADOR FAVORITO: [Nombre del jugador o N/A si no se apuesta]**

**DISTRIBUCIÓN DEL DINERO:**
[No estas obligado a apostar. Solo apuesta donde veas valor esperado positivo claro. Se trata de conseguir beneficios a largo plazo, no en un solo partido, ni en un rango de fechas corto.]
- Apuesta a Resultado del Primer Set: [Nombre del jugador] [Resultado del set (6-0, 6-1, 6-2, 6-3, 6-4, 7-5, 7-6)] [Cantidad a apostar = 1 euro o nada, siempre]

**4 FUNDAMENTALES:**
[Genera los 4 fundamentals desde la vision que has decidido.]

**Comparacion de la vision adoptada con los casos ideales:**
[Genera el resultado de la comparacion de la vision adoptada con los casos ideales, y si ha habido una coincidencia considerable, decir con cual de los casos ideales ha coincido.]

**JUSTIFICACIÓN:**
[Explicación detallada de por qué se toma esta decisión, basándose en el análisis de los debators y los informes disponibles. Explica también por qué NO se apuesta en ciertos tipos si es el caso]

**NIVEL DE CONFIANZA: [ALTO/MEDIO/BAJO]**

**RECOMENDACIONES ADICIONALES:**
[Consejos sobre cuándo ejecutar las apuestas, qué monitorear, etc.]

IMPORTANTE: 
- NO estás obligado a apostar. Solo apuesta donde veas valor esperado positivo claro. Se trata de conseguir beneficios a largo plazo, no en un solo partido, ni en un rango de fechas corto.
- SIEMPRE especifica el nombre del jugador en CADA tipo de apuesta que decidas hacer. No dejes ninguna apuesta sin indicar claramente a qué jugador se apuesta.
- Puedes poner $0 en la apuesta.
- Usa análisis matemático y probabilístico para justificar la distribución del dinero. 
- No inventes información, usa solo los datos disponibles en el debate y los informes.
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
