from tennisAgents.utils.enumerations import *
from tennisAgents.dataflows.odds_utils import fetch_betfair_odds


def create_odds_analyst(llm, toolkit):
    """
    Crea el nodo del analista de cuotas.
    NOTA: Este analista NO usa LLM, solo extrae cuotas directamente de Betfair.
    Los parámetros llm y toolkit se mantienen por compatibilidad con la estructura del grafo.
    """
    def odds_analyst_node(state):
        match_date = state[STATE.match_date]
        player = state[STATE.player_of_interest]
        opponent = state[STATE.opponent]
        tournament = state[STATE.tournament]

        print(f"\n{'='*80}")
        print(f"📊 ODDS ANALYST - Extrayendo cuotas de Betfair")
        print(f"{'='*80}")
        print(f"Jugador: {player}")
        print(f"Oponente: {opponent}")
        print(f"Torneo: {tournament}")
        print(f"Fecha: {match_date}")
        
        # Llamar directamente al scraper de Betfair
        # Intentamos buscar primero por el jugador principal
        odds_data = fetch_betfair_odds(player)
        
        # Si no se encuentra, intentar con el oponente
        if not odds_data or not odds_data.get('success', True):
            print(f"\n⚠️  No se encontró partido buscando '{player}', intentando con '{opponent}'...")
            odds_data_opp = fetch_betfair_odds(opponent)
            
            if odds_data_opp and odds_data_opp.get('success', True):
                odds_data = odds_data_opp
            elif odds_data_opp:
                odds_data = odds_data_opp
        
        # Generar el reporte basado en los datos obtenidos
        if not odds_data or not odds_data.get('success', True):
            live_events = odds_data.get('live_events', []) if odds_data else []
            live_events_str = "\n".join([f"• {e}" for e in live_events[:20]])
            if len(live_events) > 20:
                live_events_str += f"\n• ...y {len(live_events) - 20} más"
                
            if not live_events_str:
                live_events_str = "• No se encontraron eventos de tenis en juego."

            report = f"""## ❌ Error al Obtener Cuotas de Betfair

**Partido:** {player} vs {opponent}
**Torneo:** {tournament}
**Fecha:** {match_date}

**Estado:** No se pudo encontrar el partido en Betfair.

**Enlaces verificados/utilizados:**
- Betfair obtiene los partidos en juego globalmente mediante API: [Betfair Tenis En Juego](https://www.betfair.es/sport/tennis)
- Comprobar manualmente búsqueda: [Buscar {player}](https://www.betfair.es/search?q={player.replace(' ', '+')})
- Comprobar manualmente búsqueda: [Buscar {opponent}](https://www.betfair.es/search?q={opponent.replace(' ', '+')})

**Partidos en juego detectados en el momento de la búsqueda:**
{live_events_str}

**Posibles razones:**
• El partido no está actualmente "En Juego" en Betfair.
• Los nombres de los jugadores no coinciden exactamente con los de Betfair (revisa la lista arriba).
• El partido aún no ha comenzado o ya ha finalizado.
"""
        else:
            # Filtrar mercados relevantes
            filtered_markets = []
            for market in odds_data.get('markets', []):
                market_name = market.get('market_name', '')
                
                # Incluir "Cuotas de partido" y "Apuestas a sets" siempre
                if market_name in ["Cuotas de partido", "Apuestas a sets"]:
                    filtered_markets.append(market)
                    continue
                
                # Incluir mercados de "Set X - Ganador"
                if "Set" in market_name and "Ganador" in market_name and "Juego" not in market_name:
                    filtered_markets.append(market)
                    continue
                
                # Incluir mercados de "Resultado correcto del X set"
                if "Resultado correcto" in market_name:
                    filtered_markets.append(market)
                    continue
            
            # Formatear el reporte con los datos filtrados
            url_partido = f"https://www.betfair.es/sport/tennis?eventId={odds_data.get('event_id', '')}"
            report = f"""## 💰 Cuotas de Apuestas - Betfair

**Partido:** {odds_data.get('event_name', f"{player} vs {opponent}")}
**Competición:** {odds_data.get('competition', tournament)}
**Enlace del partido:** [{url_partido}]({url_partido})
**Fecha de extracción:** {odds_data.get('timestamp', match_date)}
**Total de mercados disponibles:** {len(filtered_markets)}
**Total de opciones de apuesta:** {sum(len(m.get('runners', [])) for m in filtered_markets)}

---

### 📋 Mercados y Cuotas Relevantes

"""
            # Agregar cada mercado filtrado al reporte
            if not filtered_markets:
                report += "\n⚠️ No se encontraron mercados relevantes para este partido.\n\n"
            else:
                for market in filtered_markets:
                    report += f"\n#### {market.get('market_name', 'Mercado')}\n\n"
                    
                    for runner in market.get('runners', []):
                        report += f"• **{runner.get('name')}**: {runner.get('odds')}\n"
                    
                    report += "\n"
            
            report += f"""---

### 📊 Resumen de la Extracción

**Event ID:** {odds_data.get('event_id', 'N/A')}
**Jugador buscado:** {odds_data.get('player_searched', player)}
**Estado:** ✅ Extracción exitosa
**Mercados mostrados:** {len(filtered_markets)} de {odds_data.get('total_markets', 0)} disponibles

**Nota:** Estas son cuotas reales extraídas directamente de Betfair España en tiempo real.
Solo se muestran los mercados más relevantes para la toma de decisiones de apuesta.
Los mercados y cuotas pueden variar durante el transcurso del partido.
"""

        print(f"\n{'='*80}")
        print(f"✅ Reporte de cuotas generado")
        print(f"{'='*80}\n")

        return {
            STATE.messages: [],  # No generamos mensajes de LLM
            REPORTS.odds_report: report,
        }

    return odds_analyst_node
