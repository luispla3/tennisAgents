# tennisAgents
# TFG: Sistema Inteligente de Asistencia a Apuestas en Tenis con LLM y LangGraph

Este proyecto implementa un sistema de agentes basado en LLMs (Large Language Models) y LangGraph para analizar partidos de tenis y generar recomendaciones de apuesta. El sistema toma como entrada múltiples fuentes de información (cuotas, redes sociales, noticias, jugadores, etc.) y produce una recomendación argumentada basada en distintos perfiles de riesgo (Agresivo, Conservador, Neutral) y una predicción objetiva basada en las cuotas de mercado (*Expected from Odds*).

## Objetivos

- Analizar datos heterogéneos (noticias, redes sociales, cuotas, clima, contexto del torneo).
- Simular razonamientos de distintos perfiles de analistas (agresivo, neutral, conservador).
- Generar una decisión final razonada y argumentada.
- Utilizar agentes conversacionales con LLM (Gemini o GPT).
- Aprovechar memoria contextual sobre situaciones financieras pasadas.

-- Arquitectura del Sistema - Formato ASCII (README o consola psql)

-- Estructura Lógica de Agentes y Flujo de Datos

-- Cada bloque representa un componente del sistema

/*
                          +----------------------+
                          |     LLM: Gemini      |
                          |----------------------|
                          | Players (2 calls)    |
                          | Social Media (1)     |
                          | News (1)             |
                          +----------+-----------+
                                     |
                                     v
+------------------+     +------------------+     +------------------+     +------------------+
| Tennis Players   |     | Social Media     |     | News             |     | Weather          |
| API fetch        |     | API fetch        |     | API fetch        |     | API fetch        |
+--------+---------+     +--------+---------+     +--------+---------+     +--------+---------+
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

                      [ Orquestado con LangGraph & Gemini ]
*/


## Estructura del proyecto

tennis_agents/
│
├── agents/                  # Agentes de razonamiento (basados en Gemini)
│   ├── risk_mgmt/           # Equipo de gestión de riesgos (como en TradingAgents)
│   │   ├── aggressive_agent.py
│   │   ├── neutral_agent.py
│   │   ├── conservative_agent.py
│   │   └── expected_odds.py
│   └── manager.py           # Toma la decisión final (decisión + argumentación)
│
├── data_fetchers/          # Módulos para obtener datos desde APIs externas
│   ├── players.py           # Datos de los jugadores
│   ├── social_media.py      # Opinión pública (Twitter, Reddit…)
│   ├── news.py              # Noticias relevantes
│   ├── weather.py           # Tiempo previsto
│   ├── tournament.py        # Contexto del torneo (fase, historial…)
│   └── odds.py              # Cuotas (probabilidad implícita)
│
├── memory/                 # Memoria vectorial de situaciones pasadas
│   └── memory.py
│
├── utils/                  # Herramientas auxiliares
│   ├── config.py            # Configuración general (modelos, apis…)
│   ├── prompts.py           # Plantillas de prompts reutilizables
│   └── tools.py             # Conversores, parseadores, helpers
│
├── core/                   # Núcleo del sistema (grafo y flujo de decisión)
│   ├── graph.py             # Define el LangGraph del sistema
│   └── state.py             # Define los estados del sistema (como AgentState)
│
├── interface/              # Interfaz de visualización (web, CLI o notebook)
│   ├── cli.py               # Línea de comandos
│   └── web.py               # Si decides hacer una web Flask/Streamlit
│
├── main.py                 # Script principal para pruebas
└── requirements.txt        # Dependencias del proyecto


## Requisitos

- Python 3.10+
- LangChain
- LangGraph
- OpenAI / Gemini API
- ChromaDB
- (Opcional) Gemini SDK

Instalación de dependencias:

```bash
pip install -r requirements.txt

## Ejecucion

python main.py
