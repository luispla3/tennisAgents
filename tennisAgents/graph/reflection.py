# tennis_agents/graphs/reflection.py

from typing import Dict, Any
from langchain_openai import ChatOpenAI


class Reflector:
    """Gestiona la reflexión sobre decisiones y actualiza la memoria."""

    def __init__(self, quick_thinking_llm: ChatOpenAI):
        """Inicializa el reflector con un LLM."""
        self.quick_thinking_llm = quick_thinking_llm
        self.reflection_system_prompt = self._get_reflection_prompt()

    def _get_reflection_prompt(self) -> str:
        """Devuelve el prompt base del sistema para reflexión."""
        return """
Eres un experto analista deportivo especializado en apuestas de tenis. Tu tarea es revisar decisiones y análisis realizados por los agentes, proporcionando una reflexión detallada, paso a paso, que sirva para mejorar futuras predicciones. Sigue estrictamente estas directrices:

1. Razonamiento:
   - Para cada recomendación (apostar por Jugador A, Jugador B o no apostar), determina si fue correcta o incorrecta según el resultado real del partido.
   - Analiza los factores clave que contribuyeron al acierto o fallo, como:
     - Estadísticas históricas.
     - Tendencias de forma.
     - Condiciones del torneo (superficie, clima, ronda).
     - Noticias y redes sociales.
     - Motivación y lesiones.

2. Mejora:
   - Si hubo errores, propone mejoras que ayuden a maximizar el acierto en futuras predicciones.
   - Da recomendaciones específicas (por ejemplo, “evitar confiar en rankings cuando hay lesiones recientes”).

3. Resumen:
   - Resume las lecciones aprendidas de aciertos y errores.
   - Indica cómo pueden adaptarse a próximos análisis o situaciones similares.

4. Frase clave:
   - Extrae una frase breve que sintetice la reflexión completa para usar como recordatorio en futuros análisis (máximo 1000 tokens).

Asegúrate de que tu salida sea detallada, precisa y aplicable a próximos partidos. Se te proporcionará contexto objetivo (rendimiento, sentimiento, noticias) para apoyar tu razonamiento.
"""

    def _extract_current_situation(self, current_state: Dict[str, Any]) -> str:
        """Extrae la situación actual del partido a partir del estado."""
        curr_market_report = current_state["market_report"]
        curr_sentiment_report = current_state["sentiment_report"]
        curr_news_report = current_state["news_report"]
        curr_fundamentals_report = current_state["fundamentals_report"]

        return f"{curr_market_report}\n\n{curr_sentiment_report}\n\n{curr_news_report}\n\n{curr_fundamentals_report}"

    def _reflect_on_component(
        self, component_type: str, report: str, situation: str, returns_losses
    ) -> str:
        """Genera una reflexión para un componente dado."""
        messages = [
            ("system", self.reflection_system_prompt),
            (
                "human",
                f"Resultado: {returns_losses}\n\nAnálisis o recomendación: {report}\n\nInformes objetivos del partido:\n{situation}",
            ),
        ]

        result = self.quick_thinking_llm.invoke(messages).content
        return result

    def reflect_bull_researcher(self, current_state, returns_losses, bull_memory):
        """Reflexiona sobre el análisis del agente optimista."""
        situation = self._extract_current_situation(current_state)
        bull_debate_history = current_state["investment_debate_state"]["bull_history"]

        result = self._reflect_on_component("BULL", bull_debate_history, situation, returns_losses)
        bull_memory.add_situations([(situation, result)])

    def reflect_bear_researcher(self, current_state, returns_losses, bear_memory):
        """Reflexiona sobre el análisis del agente pesimista."""
        situation = self._extract_current_situation(current_state)
        bear_debate_history = current_state["investment_debate_state"]["bear_history"]

        result = self._reflect_on_component("BEAR", bear_debate_history, situation, returns_losses)
        bear_memory.add_situations([(situation, result)])

    def reflect_trader(self, current_state, returns_losses, trader_memory):
        """Reflexiona sobre la decisión final del apostador."""
        situation = self._extract_current_situation(current_state)
        trader_decision = current_state["trader_investment_plan"]

        result = self._reflect_on_component("TRADER", trader_decision, situation, returns_losses)
        trader_memory.add_situations([(situation, result)])

    def reflect_invest_judge(self, current_state, returns_losses, invest_judge_memory):
        """Reflexiona sobre la decisión del juez de análisis."""
        situation = self._extract_current_situation(current_state)
        judge_decision = current_state["investment_debate_state"]["judge_decision"]

        result = self._reflect_on_component("INVEST JUDGE", judge_decision, situation, returns_losses)
        invest_judge_memory.add_situations([(situation, result)])

    def reflect_risk_manager(self, current_state, returns_losses, risk_manager_memory):
        """Reflexiona sobre la evaluación del gestor de riesgo."""
        situation = self._extract_current_situation(current_state)
        judge_decision = current_state["risk_debate_state"]["judge_decision"]

        result = self._reflect_on_component("RISK JUDGE", judge_decision, situation, returns_losses)
        risk_manager_memory.add_situations([(situation, result)])
