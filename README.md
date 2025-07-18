# tennisAgents
# TFG: Sistema Inteligente de Asistencia a Apuestas en Tenis con LLM y LangGraph

Este proyecto implementa un sistema de agentes basado en LLMs (Large Language Models) y LangGraph para analizar partidos de tenis y generar recomendaciones de apuesta. El sistema toma como entrada múltiples fuentes de información (cuotas, redes sociales, noticias, jugadores, etc.) y produce una recomendación argumentada basada en distintos perfiles de riesgo (Agresivo, Conservador, Neutral) y una predicción objetiva basada en las cuotas de mercado (*Expected from Odds*).

## Objetivos

- Analizar datos heterogéneos (noticias, redes sociales, cuotas, clima, contexto del torneo).
- Simular razonamientos de distintos perfiles de analistas (agresivo, neutral, conservador).
- Generar una decisión final razonada y argumentada.
- Utilizar agentes conversacionales con LLM (Gemini o GPT).
- Aprovechar memoria contextual sobre situaciones financieras pasadas.

-- Arquitectura del Sistema

### Arquitectura del Sistema

```text
                          +------------------------+
                          |     LLM: Gemini        |
                          |------------------------|
                          | Players (2 calls)      |
                          | Social Media (1)       |
                          | News (1)               |
                          | Weather (1)            |
                          | Tournament Context (1) |
                          | Market Odds (1)        |
                          +----------+-------------+
                                     |
                                     v
+------------------+     +------------------+     +------------------+     +------------------
| Tennis Players   |     | Social Media     |     | News             |     | Weather         |
| API fetch        |     | API fetch        |     | API fetch        |     | API             |
+--------+---------+     +--------+---------+     +--------+---------+     +--------+---------
         |                        |                        |                        |
         v                        v                        v                        v
+-------------------------------------------------------------------------------------------+
|                                      Risk Management Team                                 |
|-------------------------------------------------------------------------------------------|
|  Aggressive Agent        Neutral Agent        Conservative Agent        Expected (Odds)   |
+-------------------------------------------------------------------------------------------+
                                               |
                                               v
                                      +------------------+
                                      |     Manager      |
                                      |------------------|
                                      | Final decision   |
                                      | Argumentation    |
                                      +--------+---------+
                                               |
                                               v
                                    +-----------------------+
                                    | Show Recommendation   |
                                    +-----------------------+

                   [ Todos los módulos orquestados con LangGraph + Gemini ]

