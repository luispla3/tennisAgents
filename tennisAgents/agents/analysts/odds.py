from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies

def create_odds_analyst(llm, toolkit):
    def odds_analyst_node(state):
        match_date = state[STATE.match_date]
        player = state[STATE.player_of_interest]
        opponent = state[STATE.opponent]
        tournament = state[STATE.tournament]

        if toolkit.config["online_tools"]:
            tools = [toolkit.get_odds_data]
        else:
            tools = [toolkit.get_odds_data]

        # Obtener la anatomía del prompt para analista de cuotas
        anatomy = TennisAnalystAnatomies.odds_analyst()
        
        # Información de herramientas
        tools_info = (
            "• get_odds_data() - Obtiene cuotas de apuestas para torneos de tenis específicos"
        )
        
        # Lista de torneos disponibles como string para el agente
        tournament_keys = """
TORNEOS DISPONIBLES EN THE ODDS API:

ATP Tournaments:
- australian_open → tennis_atp_aus_open_singles
- australian open → tennis_atp_aus_open_singles
- french_open → tennis_atp_french_open
- french open → tennis_atp_french_open
- wimbledon → tennis_atp_wimbledon
- us_open → tennis_atp_us_open
- Us Open → tennis_atp_us_open
- indian_wells → tennis_atp_indian_wells
- miami_open → tennis_atp_miami_open
- monte_carlo → tennis_atp_monte_carlo_masters
- madrid_open → tennis_atp_madrid_open
- italian_open → tennis_atp_italian_open
- canadian_open → tennis_atp_canadian_open
- cincinnati_open → tennis_atp_cincinnati_open
- shanghai_masters → tennis_atp_shanghai_masters
- paris_masters → tennis_atp_paris_masters
- dubai → tennis_atp_dubai
- qatar_open → tennis_atp_qatar_open
- china_open → tennis_atp_china_open

WTA Tournaments:
- wta_australian_open → tennis_wta_aus_open_singles
- wta_french_open → tennis_wta_french_open
- wta_wimbledon → tennis_wta_wimbledon
- wta_us_open → tennis_wta_us_open
- wta_indian_wells → tennis_wta_indian_wells
- wta_miami_open → tennis_wta_miami_open
- wta_madrid_open → tennis_wta_madrid_open
- wta_italian_open → tennis_wta_italian_open
- wta_canadian_open → tennis_wta_canadian_open
- wta_cincinnati_open → tennis_wta_cincinnati_open
- wta_dubai → tennis_wta_dubai
- wta_qatar_open → tennis_wta_qatar_open
- wta_china_open → tennis_wta_china_open
- wta_wuhan_open → tennis_wta_wuhan_open
"""
        
        # Contexto adicional específico del análisis de cuotas
        additional_context = (
            f"{tournament_keys}\n\n"
            "PROCESO A SEGUIR:\n"
            f"1. Basándote en la fecha del partido ({match_date}) y el tipo de jugadores, selecciona el torneo más relevante de la lista anterior.\n"
            "2. IMPORTANTE: Los nombres de torneos pueden tener variaciones. Busca coincidencias parciales:\n"
            "   - 'us open' → 'tennis_atp_us_open'\n"
            "   - 'australian open' → 'tennis_atp_aus_open_singles'\n"
            "   - 'french open' → 'tennis_atp_french_open'\n"
            "   - 'wimbledon' → 'tennis_atp_wimbledon'\n"
            "3. Usa 'get_odds_data' con el tournament_key correspondiente (la parte después de →)\n"
            "4. Busca en los eventos del torneo el partido específico entre los jugadores.\n\n"
            "5. MUY IMPORTANTE: Si no se encuentra el torneo, intenta con variaciones del nombre antes de generar error.\n\n"
            "ANÁLISIS REQUERIDO:\n"
            "• Identificación del favorito según las cuotas y margen de ventaja\n"
            "• Comparación de cuotas entre diferentes casas de apuestas\n"
            "• Análisis de variaciones en las cuotas (si están disponibles)\n"
            "• Patrones que indiquen confianza del mercado en una dirección\n"
            "• Discrepancias significativas entre casas que puedan indicar oportunidades\n"
            "• Contexto del torneo y su impacto en las cuotas\n\n"
            "IMPORTANTE: Proporciona análisis específico con números concretos, no generalidades. Incluye cuotas exactas, márgenes calculados y contexto específico del mercado.\n\n"
            "SI NO PUEDES ENCONTRAR EL TORNEO O PARTIDO: Genera un reporte de error claro indicando que no se pudo obtener información de cuotas y continúa automáticamente."
        )

        # Crear prompt estructurado usando la anatomía
        prompt = PromptBuilder.create_structured_prompt(
            anatomy=anatomy,
            tools_info=tools_info,
            additional_context=additional_context
        )

        # Inyección de variables al prompt
        prompt = prompt.partial(player=player)
        prompt = prompt.partial(opponent=opponent)
        prompt = prompt.partial(match_date=match_date)

        chain = prompt | llm.bind_tools(tools)
        
        # Crear el input correcto como diccionario
        input_data = {
            "messages": state[STATE.messages],
            "user_message": f"Analiza las cuotas de apuestas para el partido entre {player} y {opponent}."
        }
        
        result = chain.invoke(input_data)

        report = ""
        if len(result.tool_calls) == 0:
            # Si no hay llamadas a herramientas, significa que no se pudo encontrar el torneo/partido
            # Generamos un reporte de error y continuamos
            report = f"""# Reporte de Análisis de Cuotas - Error

## Resumen
No se pudo obtener información de cuotas de apuestas para el partido entre **{player}** y **{opponent}** que se disputa el **{match_date}** en el torneo **{tournament}**.

## Razón del Error
El torneo "{tournament}" no se pudo mapear correctamente a una clave de The Odds API. 

## Torneos Disponibles
Los torneos disponibles incluyen:
- **Grand Slams**: Australian Open, French Open, Wimbledon, US Open
- **Masters 1000**: Indian Wells, Miami Open, Monte Carlo, Madrid Open, Italian Open, Canadian Open, Cincinnati Open, Shanghai Masters, Paris Masters
- **Otros**: Dubai, Qatar Open, China Open

## Posibles Soluciones
1. **Verificar el nombre del torneo**: Asegúrate de que coincida exactamente con los nombres listados
2. **Variaciones de nombres**: "us open" y "us_open" ambos mapean a "tennis_atp_us_open"
3. **Torneos menores**: Algunos torneos challenger o ITF pueden no estar disponibles en The Odds API

## Impacto en el Análisis
- No se pueden analizar las cuotas de apuestas para este partido
- No se puede determinar el favorito según el mercado
- No se pueden identificar oportunidades de arbitraje o discrepancias entre casas

## Recomendación
Para partidos en torneos menores o challengers, se recomienda:
- Continuar con otros análisis disponibles (jugadores, clima, noticias)
- Considerar que la falta de cuotas puede indicar menor interés del mercado
- Proceder con el análisis de riesgo basado en otros factores disponibles

---
*Este reporte se generó automáticamente debido a la falta de disponibilidad de datos de cuotas.*"""
        else:
            report = result.content

        return {
            STATE.messages: [result],
            REPORTS.odds_report: report,
        }

    return odds_analyst_node
