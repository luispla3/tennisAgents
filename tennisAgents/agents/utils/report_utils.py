"""Utilidades de post-procesado para informes de analistas."""

from __future__ import annotations

import re

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+")
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")


def sanitize_analyst_report(text: str) -> str:
    """
    Limpia artefactos comunes del LLM en informes finales.

    - Elimina caracteres CJK accidentales (p. ej. 熟悉idad).
    - Normaliza espacios repetidos tras la limpieza.
    """
    if not text:
        return text
    cleaned = _CJK_RE.sub("", text)
    cleaned = _MULTI_SPACE_RE.sub(" ", cleaned)
    lines = [line.rstrip() for line in cleaned.splitlines()]
    return "\n".join(lines).strip()
