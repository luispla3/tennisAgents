from typing import Dict, Any
from langchain_openai import ChatOpenAI

from tennisAgents.utils.enumerations import ANALYSTS, REPORTS, STATE


class Reflector:
    """Encargado de reflexionar sobre decisiones y actualizar la memoria."""

    def __init__(self, quick_thinking_llm: ChatOpenAI):
        """Inicializa el reflector con un modelo LLM."""
        self.quick_thinking_llm = quick_thinking_llm
        self.reflection_system_prompt = self._get_reflection_prompt()

    def _get_reflection_prompt(self) -> str:
        """Devuelve el prompt de reflexión."""
        return """
Eres un experto analista de tenis encargado de revisar decisiones de predicción de partidos y proporcionar un análisis detallado y paso a paso. 
Tu objetivo es ofrecer conocimientos detallados sobre la predicción, identificar aciertos y errores, y proponer mejoras claras. Sigue estrictamente estas directrices:

1. Razonamiento:
   - Determina si la predicción fue correcta o incorrecta. Una predicción correcta implica que se acertó el resultado del partido.
   - Analiza los factores que contribuyeron al éxito o al error, como:
     - Rendimiento previo de los jugadores.
     - Superficie de la pista.
     - Torneo.
     - Tendencias recientes.
     - Lesiones o noticias recientes.
     - Análisis estadístico del jugador.

2. Mejora:
   - Para decisiones incorrectas, sugiere cómo podrían mejorarse.
   - Proporciona una lista detallada de acciones correctivas (por ejemplo, evitar apostar a jugadores con mala racha en tierra batida).

3. Resumen:
   - Resume las lecciones aprendidas de los aciertos y errores.
   - Explica cómo aplicar esas lecciones a futuros partidos similares.

4. Síntesis:
   - Extrae una frase clave que resuma las lecciones más importantes (máximo 1000 tokens).

Sigue estas instrucciones con precisión y proporciona resultados detallados, razonados y aplicables. 
Recibirás también información objetiva del contexto del partido (noticias, estadísticas, etc.) para fundamentar tu análisis.
"""

    def _extract_current_situation(self, current_state: Dict[str, Any]) -> str:
        """Extrae la situación actual del contexto del partido."""
        return (
            f"{current_state[REPORTS.players_report]}\n\n"
            f"{current_state[REPORTS.news_report]}\n\n"
            f"{current_state[REPORTS.sentiment_report]}\n\n"
            f"{current_state[REPORTS.tournament_report]}\n\n"
            f"{current_state[REPORTS.odds_report]}\n\n"
            f"{current_state[REPORTS.weather_report]}\n\n"
        )

    def _reflect_on_component(
        self, role_name: str, decision_info: str, situation: str, returns_losses
    ) -> str:
        """Genera la reflexión para un componente concreto."""
        messages = [
            ("system", self.reflection_system_prompt),
            (
                "human",
                f"Resultado: {returns_losses}\n\nPredicci\u00f3n / Decisi\u00f3n: {decision_info}\n\nContexto objetivo del partido: {situation}",
            ),
        ]
        result = self.quick_thinking_llm.invoke(messages).content
        return result

    def reflect_risk_manager(self, current_state, returns_losses, risk_memory):
        """Reflexiona sobre la decisión del juez de riesgo y actualiza su memoria."""
        situation = self._extract_current_situation(current_state)
        judge_decision = current_state[STATE.risk_debate_state][STATE.judge_decision]

        result = self._reflect_on_component(
            ANALYSTS.judge, judge_decision, situation, returns_losses
        )
        risk_memory.add_situations([(situation, result)])
