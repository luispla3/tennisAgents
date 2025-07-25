from tennisAgents.utils.enumerations import *

def create_risk_manager(llm, memory):
    def risk_manager_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state[HISTORYS.history]

        # Informes previos disponibles
        weather_report = state[REPORTS.weather_report]
        odds_report = state[REPORTS.odds_report]
        sentiment_report = state[REPORTS.sentiment_report]
        news_report = state[REPORTS.news_report]
        players_report = state[REPORTS.players_report]
        tournament_report = state[REPORTS.tournament_report]

        # Memorias de errores pasados
        curr_situation = f"{weather_report}\n\n{odds_report}\n\n{sentiment_report}\n\n{news_report}\n\n{players_report}\n\n{tournament_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""Como Juez de Riesgos en un sistema de apuestas deportivas, tu objetivo es evaluar el debate entre **cuatro analistas** (Agresivo, Conservador, Neutral y Basado en Valor Esperado) y decidir si seguir el plan del trader. Tu respuesta debe incluir una **recomendación clara**:
- **APOSTAR** si el análisis es favorable y bien respaldado.
- **NO APOSTAR** si hay demasiado riesgo o señales contradictorias.
- **ESPERAR** si se necesita más información o si el análisis es demasiado ambiguo.

### Directrices para decidir:
1. **Resumir los argumentos clave** de los analistas, indicando fortalezas y debilidades de cada uno.
2. **Justificar tu decisión** basándote en el contenido del debate y en los informes (cuotas, estado del jugador, torneo, clima, etc.).
3. **Ajustar el plan del trader**: Evalúa si la apuesta propuesta debe modificarse (por ejemplo, esperar un mejor momento o apostar una cantidad menor).
4. **Aprender de errores pasados**: Usa la memoria histórica para evitar repetir decisiones incorrectas, como apuestas que resultaron en pérdidas por mal juicio.

### Debate actual entre analistas:
{history}

### Lecciones aprendidas de situaciones similares:
{past_memory_str}

Tu respuesta debe ser clara, razonada y orientada a la toma de decisiones óptimas. No repitas todos los informes, céntrate en la conclusión y en cómo se ha llegado a ella."""

        response = llm.invoke(prompt)

        new_risk_debate_state = {
            "judge_decision": response.content,
            HISTORYS.history: history,
            HISTORYS.aggressive_history: risk_debate_state.get(HISTORYS.aggressive_history, ""),
            HISTORYS.safe_history: risk_debate_state.get(HISTORYS.safe_history, ""),
            HISTORYS.neutral_history: risk_debate_state.get(HISTORYS.neutral_history, ""),
            HISTORYS.expected_history: risk_debate_state.get(HISTORYS.expected_history, ""),
            "latest_speaker": SPEAKERS.judge,
            RESPONSES.aggressive: risk_debate_state.get(RESPONSES.aggressive, ""),
            RESPONSES.safe: risk_debate_state.get(RESPONSES.safe, ""),
            RESPONSES.neutral: risk_debate_state.get(RESPONSES.neutral, ""),
            RESPONSES.expected: risk_debate_state.get(RESPONSES.expected, ""),
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_betting_decision": response.content,
        }

    return risk_manager_node
