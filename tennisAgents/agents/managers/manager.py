import concurrent.futures
from typing import Dict, Any, Optional

from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.memory import chunk_text

def _execute_single_risk_manager(llm, state: Dict[str, Any], memory, model_name: str) -> tuple[str, str]:
    """
    Ejecuta un risk manager individual y devuelve su decisión.
    
    Returns:
        tuple: (model_name, decision)
    """
    risk_debate_state = state.get(STATE.risk_debate_state, {})
    history = risk_debate_state.get(HISTORYS.history, "")

    # Informes previos disponibles
    weather_report = state.get(REPORTS.weather_report, "")
    odds_report = state.get(REPORTS.odds_report, "")
    sentiment_report = state.get(REPORTS.sentiment_report, "")
    news_report = state.get(REPORTS.news_report, "")
    players_report = state.get(REPORTS.players_report, "")
    tournament_report = state.get(REPORTS.tournament_report, "")
    match_live_report = state.get(REPORTS.match_live_report, "")
    
    # Información del usuario y partido
    wallet_balance = state.get(STATE.wallet_balance, 0)
    match_date = state.get(STATE.match_date, "")
    player_of_interest = state.get(STATE.player_of_interest, "")
    opponent = state.get(STATE.opponent, "")
    tournament = state.get(STATE.tournament, "")

    # Memorias de errores pasados (si memory está disponible)
    past_memory_str = ""
    if memory:
        curr_situation = f"{weather_report}\n\n{odds_report}\n\n{sentiment_report}\n\n{news_report}\n\n{players_report}\n\n{tournament_report}\n\n{match_live_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

    prompt = f"""
Como Juez de Riesgos en un sistema de apuestas deportivas, tu objetivo es evaluar el debate entre **cuatro managers** (Agresivo, Conservador, Neutral y Basado en Valor Esperado) desde una perspectiva probabilisticamente rentable, y generar un INFORME FINAL ESTRUCTURADO y CLARO sobre la decisión de apuesta.

**INFORMACIÓN DEL PARTIDO:**
- Saldo disponible: ${wallet_balance}
- Fecha: {match_date}
- Jugador de interés: {player_of_interest}
- Oponente: {opponent}
- Torneo: {tournament}

### TU TAREA:
Genera un INFORME FINAL que incluya:

1. **DECISIÓN PRINCIPAL**: ¿APOSTAR o NO APOSTAR?
2. **DISTRIBUCIÓN DEL DINERO**: Qué apuesta/s se hace/n y cuanto se apuesta/n, teniendo en cuenta el saldo disponible ${wallet_balance}. No apostar mas del 10% del saldo disponible sumando todas las apuestas a realizar.
3. **VISION ADOPTADA**: La vision adoptada que has decidido seguir.
4. **JUSTIFICACIÓN COMPLETA**: Por qué se toma esta decisión.

### TIPO DE APUESTA A CONSIDERAR:
1. **Cuotas de partido** - Que jugador gana el partido. **OBLIGATORIO APOSTAR SIEMPRE**: Debes apostar siempre a este tipo de apuesta, aunque no haya valor esperado positivo. Simplemente apuesta al jugador más probable de ganar el partido según tu análisis.
2. **Apuestas a sets** - Que jugador gana el partido, determinando los X-Y sets en que gana el partido. **OBLIGATORIO APOSTAR SIEMPRE**: Debes apostar siempre a este tipo de apuesta, aunque no haya valor esperado positivo. Simplemente apuesta al jugador más probable según tu análisis.
3. **Set X - Ganador** - Que jugador gana el set X. **OBLIGATORIO APOSTAR SIEMPRE**: Debes apostar siempre a este tipo de apuesta, aunque no haya valor esperado positivo. Simplemente apuesta al jugador más probable de ganar el set X según tu análisis.
4. **Set X - Resultado correcto** - Que jugador gana el set X y el resultado del set (6-0, 6-1, 6-2, 6-3, 6-4, 7-5, 7-6). **OBLIGATORIO APOSTAR SIEMPRE**: Debes apostar siempre a este tipo de apuesta, aunque no haya valor esperado positivo. Simplemente apuesta al jugador más probable según tu análisis.

### Informe de Cuotas Disponibles (Betfair):
{odds_report}

### Debate actual entre analistas:
{history}

### Lecciones aprendidas de situaciones similares:
{past_memory_str}

### FORMATO DEL INFORME FINAL:
Tu respuesta debe seguir EXACTAMENTE esta estructura:

**DECISIÓN FINAL: [APOSTAR/NO APOSTAR]**

**JUGADOR FAVORITO: [Nombre del jugador o N/A si no se apuesta]**

**DISTRIBUCIÓN DEL DINERO:**
[IMPORTANTE: Las 4 modalidades de apuestas ("Cuotas de partido", "Apuestas a sets", "Set X - Ganador", y "Set X - Resultado correcto") son OBLIGATORIAS y debes apostar siempre, aunque no haya valor esperado positivo. Simplemente apuesta al jugador más probable según tu análisis. Se trata de conseguir beneficios a medio y largo plazo, no en un solo partido, ni en un rango de fechas corto. No apostar mas del 10% del saldo disponible sumando todas las apuestas a realizar.]
- Cuotas de partido: [OBLIGATORIO - Nombre del jugador ganador de la apuesta] [valor de la apuesta (*1.5, *2, *3...)] [Cantidad a apostar] [Confianza en la apuesta (0-10)]
- Apuestas a sets: [OBLIGATORIO - Nombre del jugador ganador de la apuesta] [X-Y sets] [valor de la apuesta (*1.5, *2, *3...)] [Cantidad a apostar] [Confianza en la apuesta (0-10)]
- Set X - Ganador: [OBLIGATORIO - Nombre del jugador ganador de la apuesta] [valor de la apuesta (*1.5, *2, *3...)] [Cantidad a apostar] [Confianza en la apuesta (0-10)]
- Set X - Resultado correcto: [OBLIGATORIO - Nombre del jugador ganador de la apuesta] [Resultado del set (6-0, 6-1, 6-2, 6-3, 6-4, 7-5, 7-6)] [valor de la apuesta (*1.5, *2, *3...)] [Cantidad a apostar] [Confianza en la apuesta (0-10)]

**JUSTIFICACIÓN:**
[Explicación detallada de por qué se toma esta decisión, basándose en el análisis de los managers y los informes disponibles. Explica también por qué NO se apuesta en ciertos tipos si es el caso]

**NIVEL DE CONFIANZA DE LA ESTRATEGIA FINAL: [0-10]**

**RECOMENDACIONES ADICIONALES:**
[Consejos sobre cuándo ejecutar las apuestas, qué monitorear, etc.]

IMPORTANTE: 
- **OBLIGATORIO APOSTAR SIEMPRE**: Las 4 modalidades de apuestas ("Cuotas de partido", "Apuestas a sets", "Set X - Ganador" y "Set X - Resultado correcto") son OBLIGATORIAS. Debes apostar siempre a estos tipos de apuesta, aunque no haya valor esperado positivo. Simplemente apuesta al jugador más probable de ganar según tu análisis probabilístico.
- Se trata de conseguir beneficios a medio y largo plazo, no en un solo partido, ni en un rango de fechas corto. No apostar mas del 10% del saldo disponible sumando todas las apuestas a realizar.
- SIEMPRE especifica el nombre del jugador en CADA tipo de apuesta que decidas hacer. No dejes ninguna apuesta sin indicar claramente a qué jugador se apuesta.
- Usa análisis matemático y probabilístico para justificar la distribución del dinero. 
- **IMPORTANTE**: Consulta SIEMPRE el "Informe de Cuotas Disponibles (Betfair)" para obtener las cuotas exactas. NO inventes cuotas ni uses cuotas del debate si no están verificadas en el informe de cuotas. Si una cuota no aparece en el informe, indica "N/A" en lugar de inventar un valor.
- No inventes información, usa solo los datos disponibles en el debate y los informes.
- En todas las apuestas, buscamos rentabilidades a futuro.
"""

    try:
        response = llm.invoke(prompt)
        decision = response.content if hasattr(response, 'content') else str(response)
        return (model_name, decision)
    except Exception as e:
        return (model_name, f"Error al ejecutar risk manager {model_name}: {str(e)}")

def create_risk_manager(llm, memory, additional_risk_managers: Optional[list] = None):
    """
    Crea un risk manager node que ejecuta el risk manager principal y, en paralelo,
    ejecuta risk managers adicionales para generar reportes individuales de cada modelo.
    
    Args:
        llm: LLM principal para el risk manager
        memory: Memoria para el risk manager
        additional_risk_managers: Lista opcional de tuplas (model_name, llm) para risk managers adicionales
    """
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

        # Memorias de errores pasados
        curr_situation = f"{weather_report}\n\n{odds_report}\n\n{sentiment_report}\n\n{news_report}\n\n{players_report}\n\n{tournament_report}\n\n{match_live_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""
Como Juez de Riesgos en un sistema de apuestas deportivas, tu objetivo es evaluar el debate entre **cuatro managers** (Agresivo, Conservador, Neutral y Basado en Valor Esperado) desde una perspectiva probabilisticamente rentable, y generar un INFORME FINAL ESTRUCTURADO y CLARO sobre la decisión de apuesta.

**INFORMACIÓN DEL PARTIDO:**
- Saldo disponible: ${wallet_balance}
- Fecha: {match_date}
- Jugador de interés: {player_of_interest}
- Oponente: {opponent}
- Torneo: {tournament}

### TU TAREA:
Genera un INFORME FINAL que incluya:

1. **DECISIÓN PRINCIPAL**: ¿APOSTAR o NO APOSTAR?
2. **DISTRIBUCIÓN DEL DINERO**: Qué apuesta/s se hace/n y cuanto se apuesta/n, teniendo en cuenta el saldo disponible ${wallet_balance}. No apostar mas del 10% del saldo disponible sumando todas las apuestas a realizar.
3. **VISION ADOPTADA**: La vision adoptada que has decidido seguir.
4. **JUSTIFICACIÓN COMPLETA**: Por qué se toma esta decisión.

### TIPO DE APUESTA A CONSIDERAR:
1. **Cuotas de partido** - Que jugador gana el partido. **OBLIGATORIO APOSTAR SIEMPRE**: Debes apostar siempre a este tipo de apuesta, aunque no haya valor esperado positivo. Simplemente apuesta al jugador más probable de ganar el partido según tu análisis.
2. **Apuestas a sets** - Que jugador gana el partido, determinando los X-Y sets en que gana el partido. **OBLIGATORIO APOSTAR SIEMPRE**: Debes apostar siempre a este tipo de apuesta, aunque no haya valor esperado positivo. Simplemente apuesta al jugador más probable según tu análisis.
3. **Set X - Ganador** - Que jugador gana el set X. **OBLIGATORIO APOSTAR SIEMPRE**: Debes apostar siempre a este tipo de apuesta, aunque no haya valor esperado positivo. Simplemente apuesta al jugador más probable de ganar el set X según tu análisis.
4. **Set X - Resultado correcto** - Que jugador gana el set X y el resultado del set (6-0, 6-1, 6-2, 6-3, 6-4, 7-5, 7-6). **OBLIGATORIO APOSTAR SIEMPRE**: Debes apostar siempre a este tipo de apuesta, aunque no haya valor esperado positivo. Simplemente apuesta al jugador más probable según tu análisis.

### Informe de Cuotas Disponibles (Betfair):
{odds_report}

### Debate actual entre analistas:
{history}

### Lecciones aprendidas de situaciones similares:
{past_memory_str}

### FORMATO DEL INFORME FINAL:
Tu respuesta debe seguir EXACTAMENTE esta estructura:

**DECISIÓN FINAL: [APOSTAR/NO APOSTAR]**

**JUGADOR FAVORITO: [Nombre del jugador o N/A si no se apuesta]**

**DISTRIBUCIÓN DEL DINERO:**
[IMPORTANTE: Las 4 modalidades de apuestas ("Cuotas de partido", "Apuestas a sets", "Set X - Ganador", y "Set X - Resultado correcto") son OBLIGATORIAS y debes apostar siempre, aunque no haya valor esperado positivo. Simplemente apuesta al jugador más probable según tu análisis. Se trata de conseguir beneficios a medio y largo plazo, no en un solo partido, ni en un rango de fechas corto. No apostar mas del 10% del saldo disponible sumando todas las apuestas a realizar.]
- Cuotas de partido: [OBLIGATORIO - Nombre del jugador ganador de la apuesta] [valor de la apuesta (*1.5, *2, *3...)] [Cantidad a apostar] [Confianza en la apuesta (0-10)]
- Apuestas a sets: [OBLIGATORIO - Nombre del jugador ganador de la apuesta] [X-Y sets] [valor de la apuesta (*1.5, *2, *3...)] [Cantidad a apostar] [Confianza en la apuesta (0-10)]
- Set X - Ganador: [OBLIGATORIO - Nombre del jugador ganador de la apuesta] [valor de la apuesta (*1.5, *2, *3...)] [Cantidad a apostar] [Confianza en la apuesta (0-10)]
- Set X - Resultado correcto: [OBLIGATORIO - Nombre del jugador ganador de la apuesta] [Resultado del set (6-0, 6-1, 6-2, 6-3, 6-4, 7-5, 7-6)] [valor de la apuesta (*1.5, *2, *3...)] [Cantidad a apostar] [Confianza en la apuesta (0-10)]

**JUSTIFICACIÓN:**
[Explicación detallada de por qué se toma esta decisión, basándose en el análisis de los managers y los informes disponibles. Explica también por qué NO se apuesta en ciertos tipos si es el caso]

**NIVEL DE CONFIANZA DE LA ESTRATEGIA FINAL: [0-10]**

**RECOMENDACIONES ADICIONALES:**
[Consejos sobre cuándo ejecutar las apuestas, qué monitorear, etc.]

IMPORTANTE: 
- **OBLIGATORIO APOSTAR SIEMPRE**: Las 4 modalidades de apuestas ("Cuotas de partido", "Apuestas a sets", "Set X - Ganador" y "Set X - Resultado correcto") son OBLIGATORIAS. Debes apostar siempre a estos tipos de apuesta, aunque no haya valor esperado positivo. Simplemente apuesta al jugador más probable de ganar según tu análisis probabilístico.
- Se trata de conseguir beneficios a medio y largo plazo, no en un solo partido, ni en un rango de fechas corto. No apostar mas del 10% del saldo disponible sumando todas las apuestas a realizar.
- SIEMPRE especifica el nombre del jugador en CADA tipo de apuesta que decidas hacer. No dejes ninguna apuesta sin indicar claramente a qué jugador se apuesta.
- Usa análisis matemático y probabilístico para justificar la distribución del dinero. 
- **IMPORTANTE**: Consulta SIEMPRE el "Informe de Cuotas Disponibles (Betfair)" para obtener las cuotas exactas. NO inventes cuotas ni uses cuotas del debate si no están verificadas en el informe de cuotas. Si una cuota no aparece en el informe, indica "N/A" en lugar de inventar un valor.
- No inventes información, usa solo los datos disponibles en el debate y los informes.
- En todas las apuestas, buscamos rentabilidades a futuro.
"""

        # Ejecutar el risk manager principal
        main_response = llm.invoke(prompt)
        main_decision = main_response.content if hasattr(main_response, 'content') else str(main_response)
        
        # Obtener el nombre del modelo principal del LLM
        try:
            main_model_name = llm.model_name if hasattr(llm, 'model_name') else getattr(llm, '_model_name', None) or getattr(llm, 'model', 'Principal')
        except:
            main_model_name = "Principal"
        
        # Inicializar el diccionario de decisiones individuales
        individual_decisions = {main_model_name: main_decision}
        
        # Ejecutar risk managers adicionales en paralelo si están disponibles
        if additional_risk_managers:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(additional_risk_managers)) as executor:
                future_to_manager = {
                    executor.submit(_execute_single_risk_manager, additional_llm, state, memory, model_name): model_name
                    for model_name, additional_llm in additional_risk_managers
                }
                
                for future in concurrent.futures.as_completed(future_to_manager):
                    try:
                        model_name, decision = future.result()
                        individual_decisions[model_name] = decision
                    except Exception as e:
                        model_name = future_to_manager[future]
                        individual_decisions[model_name] = f"Error al ejecutar: {str(e)}"

        new_risk_debate_state = {
            STATE.judge_decision: main_decision,  # Mantener la decisión principal para compatibilidad
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
            STATE.final_bet_decision: main_decision,  # Mantener la decisión principal como final_bet_decision
            STATE.individual_risk_manager_decisions: individual_decisions,  # Guardar todas las decisiones individuales
        }

    return risk_manager_node
