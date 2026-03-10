from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, RiskDebatorAnatomies


def create_neutral_debator(llm):
    def neutral_node(state) -> dict:
        risk_debate_state = state[STATE.risk_debate_state]
        history = risk_debate_state.get(HISTORYS.history, "")
        neutral_history = risk_debate_state.get(HISTORYS.neutral_history, "")

        current_aggressive_response = risk_debate_state.get(RESPONSES.aggressive, "")
        current_safe_response = risk_debate_state.get(RESPONSES.safe, "")
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

        anatomy = RiskDebatorAnatomies.neutral_debator()

        additional_context = (
            "INFORMACIÓN DEL USUARIO Y PARTIDO:\n"
            "- Fecha del partido: {match_date}\n"
            "- Jugador de interés: {player_of_interest}\n"
            "- Oponente: {opponent}\n"
            "- Torneo: {tournament}\n"
            "- Saldo disponible: ${wallet_balance}\n\n"
            "DETALLES OBLIGATORIOS DE LA TAREA:\n"
            "- Debes construir tu razonamiento a partir de los reportes disponibles desde una visión equilibrada entre la opción más probable y las oportunidades de inversión.\n"
            "- Debes estudiar las cuotas de apuestas disponibles.\n"
            "- Debes contrastar la evidencia de los reportes con las cuotas para comprobar tanto si la opción más probable está bien reflejada como si existen oportunidades moderadas con buen balance riesgo-beneficio.\n"
            "- La estrategia de inversión debe equilibrar inversiones seguras y probables con oportunidades moderadamente arriesgadas pero con buen valor.\n"
            "- Si no existe ninguna oportunidad de inversión con buen equilibrio, debes decir explícitamente que no se apuesta.\n\n"
            "INFORMES DISPONIBLES:\n"
            "- Pronóstico del tiempo: {weather_report}\n"
            "- Informe de cuotas de apuestas: {odds_report}\n"
            "- Sentimiento en redes sociales: {sentiment_report}\n"
            "- Noticias recientes: {news_report}\n"
            "- Informe comparativo de jugadores: {players_report}\n"
            "- Información del torneo: {tournament_report}\n"
            "- Estado del partido en vivo: {match_live_report}\n\n"
            "ARGUMENTOS PREVIOS:\n"
            "- Analista conservadora: {current_safe_response}\n"
            "- Analista agresivo: {current_aggressive_response}\n"
            "- Analista de probabilidades: {current_expected_response}\n\n"
            "HISTORIAL DE DEBATE:\n"
            "{history}\n\n"
            "REQUISITOS DE RESPUESTA NO NEGOCIABLES:\n"
            "- Selecciona libremente los factores que consideres más relevantes según la evidencia disponible.\n"
            "- Explica tu estrategia de inversión equilibrada para las cuotas o el mercado analizado, balanceando probabilidad y valor.\n"
            "- Justifica matemáticamente por qué el enfoque equilibrado tiene sentido dadas las circunstancias.\n"
            "- Rebate directamente los argumentos de los analistas agresivo y conservador.\n"
            "- Si no hay una oportunidad equilibrada con base suficiente, dilo explícitamente.\n"
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
        prompt = prompt.partial(current_safe_response=current_safe_response)
        prompt = prompt.partial(current_aggressive_response=current_aggressive_response)
        prompt = prompt.partial(current_expected_response=current_expected_response)
        prompt = prompt.partial(history=history)

        chain = prompt | llm

        input_data = {
            "user_message": (
                f"Defiende la postura neutral para {player_of_interest} vs {opponent}. "
                "Analiza la evidencia disponible, las cuotas y una estrategia de inversión balanceando probabilidad y valor sin inversiones contradictorias."
            )
        }

        response = chain.invoke(input_data)

        argument = f"Neutral Analyst: {response.content}"

        new_risk_debate_state = {
            HISTORYS.history: history + "\n" + argument,
            HISTORYS.aggressive_history: risk_debate_state.get(HISTORYS.aggressive_history, ""),
            HISTORYS.safe_history: risk_debate_state.get(HISTORYS.safe_history, ""),
            HISTORYS.neutral_history: neutral_history + "\n" + argument,
            HISTORYS.expected_history: risk_debate_state.get(HISTORYS.expected_history, ""),
            STATE.latest_speaker: SPEAKERS.neutral,
            RESPONSES.aggressive: risk_debate_state.get(RESPONSES.aggressive, ""),
            RESPONSES.safe: risk_debate_state.get(RESPONSES.safe, ""),
            RESPONSES.neutral: argument,
            RESPONSES.expected: risk_debate_state.get(RESPONSES.expected, ""),
            STATE.count: risk_debate_state.get(STATE.count, 0) + 1,
        }

        return {STATE.risk_debate_state: new_risk_debate_state}

    return neutral_node
