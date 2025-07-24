# tennis_agents/graphs/signal_processing.py

from langchain_openai import ChatOpenAI


class SignalProcessor:
    """Procesa señales de análisis para extraer decisiones de apuesta."""

    def __init__(self, quick_thinking_llm: ChatOpenAI):
        """Inicializa el procesador con un LLM."""
        self.quick_thinking_llm = quick_thinking_llm

    def process_signal(self, full_signal: str) -> str:
        """
        Procesa una recomendación de análisis para extraer la decisión principal.

        Args:
            full_signal: Texto completo con la recomendación de apuesta

        Returns:
            Decisión extraída: APOSTAR_JUGADOR_A, APOSTAR_JUGADOR_B, o NO_APOSTAR
        """
        messages = [
            (
                "system",
                "Eres un asistente eficiente diseñado para analizar párrafos o informes generados por analistas deportivos. "
                "Tu tarea es extraer la decisión de apuesta: APOSTAR_JUGADOR_A, APOSTAR_JUGADOR_B o NO_APOSTAR. "
                "Devuelve únicamente la decisión extraída, sin añadir ninguna explicación o texto adicional.",
            ),
            ("human", full_signal),
        ]

        return self.quick_thinking_llm.invoke(messages).content.strip()
