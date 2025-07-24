def create_risk_manager(llm, memory):
    def risk_manager_node(state) -> dict:
        match_id = state["match_id"]
        trader_plan = state["trader_plan"]

        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state["history"]

        # Informes previos disponibles
        weather_report = state["weather_report"]
        odds_report = state["odds_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        tournament_report = state["tournament_report"]

        # Memorias de errores pasados
        curr_situation = f"{weather_report}\n\n{odds_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}\n\n{tournament_report}"
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

### Plan original del Trader:
{trader_plan}

### Lecciones aprendidas de situaciones similares:
{past_memory_str}

Tu respuesta debe ser clara, razonada y orientada a la toma de decisiones óptimas. No repitas todos los informes, céntrate en la conclusión y en cómo se ha llegado a ella."""

        response = llm.invoke(prompt)

        new_risk_debate_state = {
            "judge_decision": response.content,
            "history": history,
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "expected_history": risk_debate_state.get("expected_history", ""),
            "latest_speaker": "Judge",
            "current_aggressive_response": risk_debate_state.get("current_aggressive_response", ""),
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
            "current_expected_response": risk_debate_state.get("current_expected_response", ""),
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_betting_decision": response.content,
        }

    return risk_manager_node
