from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, RiskDebatorAnatomies


def create_conservative_debator(llm):
    def conservative_node(state) -> dict:
        risk_debate_state = state[STATE.risk_debate_state]
        history = risk_debate_state.get(HISTORYS.history, "")
        safe_history = risk_debate_state.get(HISTORYS.safe_history, "")

        current_aggressive_response = risk_debate_state.get(RESPONSES.aggressive, "")
        current_neutral_response = risk_debate_state.get(RESPONSES.neutral, "")
        current_expected_response = risk_debate_state.get(RESPONSES.expected, "")

        # Informes disponibles
        news_report = state[REPORTS.news_report]
        odds_report = state[REPORTS.odds_report]
        players_report = state[REPORTS.players_report]
        sentiment_report = state[REPORTS.sentiment_report]
        tournament_report = state[REPORTS.tournament_report]
        weather_report = state[REPORTS.weather_report]
        match_live_report = state.get(REPORTS.match_live_report, "")

        # Información del usuario y partido
        wallet_balance = state.get(STATE.wallet_balance, 0)
        match_date = state.get(STATE.match_date, "")
        player_of_interest = state.get(STATE.player_of_interest, "")
        opponent = state.get(STATE.opponent, "")
        tournament = state.get(STATE.tournament, "")

        anatomy = RiskDebatorAnatomies.conservative_debator()

        additional_context = (
            "INFORMACIÓN DEL USUARIO Y PARTIDO:\n"
            "- Fecha del partido: {match_date}\n"
            "- Jugador de interés: {player_of_interest}\n"
            "- Oponente: {opponent}\n"
            "- Torneo: {tournament}\n"
            "- Saldo disponible: ${wallet_balance}\n\n"
            "DETALLES OBLIGATORIOS DE LA TAREA:\n"
            "- Debes construir tu razonamiento a partir de los reportes disponibles desde una visión enfocada en la opción más probable.\n"
            "- Debes estudiar las cuotas de apuestas disponibles.\n"
            "- Debes contrastar la evidencia de los reportes con las cuotas para comprobar si la opción más probable está correctamente reflejada en el mercado.\n"
            "- La estrategia de inversión debe enfocarse en la opción más probable de acertar; si no existe oportunidad segura y probable, debes decir explícitamente que no se apuesta.\n"
            "- Buscamos inversiones con alta probabilidad de éxito, no innovaciones.\n\n"
            "INFORMES DISPONIBLES:\n"
            "- Pronóstico del tiempo: {weather_report}\n"
            "- Informe de cuotas de apuestas: {odds_report}\n"
            "- Sentimiento en redes sociales: {sentiment_report}\n"
            "- Noticias recientes: {news_report}\n"
            "- Informe comparativo de jugadores: {players_report}\n"
            "- Información del torneo: {tournament_report}\n"
            "- Estado del partido en vivo: {match_live_report}\n\n"
            "ARGUMENTOS PREVIOS:\n"
            "- Analista agresivo: {current_aggressive_response}\n"
            "- Analista neutral: {current_neutral_response}\n"
            "- Analista de probabilidades: {current_expected_response}\n\n"
            "HISTORIAL DE DEBATE:\n"
            "{history}\n\n"
            "REQUISITOS DE RESPUESTA NO NEGOCIABLES:\n"
            "- Selecciona libremente los factores que consideres más relevantes según la evidencia disponible.\n"
            "- Explica tu estrategia de inversión conservadora para las cuotas o el mercado analizado, enfocada en la opción más probable de acertar.\n"
            "- Justifica matemáticamente por qué la perspectiva más probable tiene sentido dadas las circunstancias.\n"
            "- Rebate directamente los argumentos de los analistas agresivo y neutral.\n"
            "- Si no hay una oportunidad conservadora con base suficiente, dilo explícitamente.\n"
            "- Tu respuesta debe ser conversacional, directa y persuasiva.\n"
            "- No inventes información si no hay respuestas previas."
        )

        prompt = PromptBuilder.create_debator_prompt(
            anatomy=anatomy,
            additional_context=additional_context,
        )

        prompt = prompt.partial(match_date=match_date)
        prompt = prompt.partial(player_of_interest=player_of_interest)
        prompt = prompt.partial(opponent=opponent)
        prompt = prompt.partial(tournament=tournament)
        prompt = prompt.partial(wallet_balance=wallet_balance)
        prompt = prompt.partial(weather_report=weather_report)
        prompt = prompt.partial(odds_report=odds_report)
        prompt = prompt.partial(sentiment_report=sentiment_report)
        prompt = prompt.partial(news_report=news_report)
        prompt = prompt.partial(players_report=players_report)
        prompt = prompt.partial(tournament_report=tournament_report)
        prompt = prompt.partial(match_live_report=match_live_report)
        prompt = prompt.partial(current_aggressive_response=current_aggressive_response)
        prompt = prompt.partial(current_neutral_response=current_neutral_response)
        prompt = prompt.partial(current_expected_response=current_expected_response)
        prompt = prompt.partial(history=history)

        chain = prompt | llm

        input_data = {
            "user_message": (
                f"Defiende la postura conservadora para {player_of_interest} vs {opponent}. "
                "Analiza la evidencia disponible, las cuotas y una estrategia de inversión priorizando la opción más probable y sin inversiones contradictorias."
            )
        }

        response = chain.invoke(input_data)

        argument = f"Safe Analyst: {response.content}"

        new_risk_debate_state = {
            HISTORYS.history: history + "\n" + argument,
            HISTORYS.aggressive_history: risk_debate_state.get(HISTORYS.aggressive_history, ""),
            HISTORYS.safe_history: safe_history + "\n" + argument,
            HISTORYS.neutral_history: risk_debate_state.get(HISTORYS.neutral_history, ""),
            HISTORYS.expected_history: risk_debate_state.get(HISTORYS.expected_history, ""),
            STATE.latest_speaker: SPEAKERS.safe,
            RESPONSES.aggressive: risk_debate_state.get(RESPONSES.aggressive, ""),
            RESPONSES.safe: argument,
            RESPONSES.neutral: risk_debate_state.get(RESPONSES.neutral, ""),
            RESPONSES.expected: risk_debate_state.get(RESPONSES.expected, ""),
            STATE.count: risk_debate_state.get(STATE.count, 0) + 1,
        }

        return {STATE.risk_debate_state: new_risk_debate_state}

    return conservative_node
