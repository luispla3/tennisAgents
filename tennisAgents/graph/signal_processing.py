# tennis_agents/graphs/signal_processing.py

import json
import re

from langchain_openai import ChatOpenAI


class SignalProcessor:
    """Procesa señales de análisis para extraer decisiones de apuesta."""

    def __init__(self, quick_thinking_llm: ChatOpenAI):
        """Inicializa el procesador con un LLM."""
        self.quick_thinking_llm = quick_thinking_llm

    def _parse_structured_signal(self, full_signal: str) -> str | None:
        """Extrae la decisión desde JSON legacy o markdown del generalista."""
        try:
            data = json.loads(full_signal)
            call = data.get("target", {}).get("tool_call", {})
            name = call.get("name")
            if name in {"wait", "close"}:
                return "NO_APOSTAR"
            if name == "bet":
                option = str(call.get("arguments", {}).get("option", "")).lower()
                match = data.get("match", {})
                player_a = str(match.get("player_a", "")).lower()
                player_b = str(match.get("player_b", "")).lower()
                if player_a and (player_a in option or player_a.split()[-1] in option):
                    return "APOSTAR_JUGADOR_A"
                if player_b and (player_b in option or player_b.split()[-1] in option):
                    return "APOSTAR_JUGADOR_B"
            return None
        except json.JSONDecodeError:
            pass

        if re.search(r"## Acción: (Esperar|Cerrar)", full_signal):
            return "NO_APOSTAR"

        if re.search(r"## Acción: Apostar", full_signal):
            header = re.search(r"# Decisión Final — (.+?) vs (.+)", full_signal)
            selection = re.search(r"\*\*Selección:\*\* (.+)", full_signal)
            if header and selection:
                player_a = header.group(1).strip().lower()
                player_b = header.group(2).strip().lower()
                option = selection.group(1).strip().lower()
                if player_a and (player_a in option or player_a.split()[-1] in option):
                    return "APOSTAR_JUGADOR_A"
                if player_b and (player_b in option or player_b.split()[-1] in option):
                    return "APOSTAR_JUGADOR_B"

        return None

    def process_signal(self, full_signal: str) -> str:
        """
        Procesa una recomendación de análisis para extraer la decisión principal.

        Args:
            full_signal: Texto completo con la recomendación de apuesta

        Returns:
            Decisión extraída: APOSTAR_JUGADOR_A, APOSTAR_JUGADOR_B, o NO_APOSTAR
        """
        parsed = self._parse_structured_signal(full_signal)
        if parsed:
            return parsed

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
