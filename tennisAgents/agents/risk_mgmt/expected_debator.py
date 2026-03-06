from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, RiskDebatorAnatomies


def create_expected_debator(llm):
    def expected_node(state) -> dict:
        risk_debate_state = state[STATE.risk_debate_state]
        history = risk_debate_state.get(HISTORYS.history, "")
        expected_history = risk_debate_state.get(HISTORYS.expected_history, "")

        current_aggressive_response = risk_debate_state.get(RESPONSES.aggressive, "")
        current_neutral_response = risk_debate_state.get(RESPONSES.neutral, "")
        current_safe_response = risk_debate_state.get(RESPONSES.safe, "")

        # Informes disponibles
        weather_report = state[REPORTS.weather_report]
        odds_report = state[REPORTS.odds_report]
        sentiment_report = state[REPORTS.sentiment_report]
        news_report = state[REPORTS.news_report]
        players_report = state[REPORTS.players_report]
        tournament_report = state[REPORTS.tournament_report]
        match_live_report = state.get(REPORTS.match_live_report, "")

        # Información del usuario y partido
        wallet_balance = state.get(STATE.wallet_balance, 0)
        match_date = state.get(STATE.match_date, "")
        player_of_interest = state.get(STATE.player_of_interest, "")
        opponent = state.get(STATE.opponent, "")
        tournament = state.get(STATE.tournament, "")

        anatomy = RiskDebatorAnatomies.expected_debator()

        additional_context = (
            "INFORMACIÓN DEL PARTIDO:\n"
            "- Jugador: {player_of_interest} vs {opponent}\n"
            "- Torneo: {tournament}\n"
            "- Fecha: {match_date} | Saldo: ${wallet_balance}\n\n"
            "DETALLES OBLIGATORIOS DEL ANÁLISIS:\n"
            "- Para cada odd disponible en {odds_report}, debes determinar la probabilidad implícita.\n"
            "- Si la odd es *10, la casa implica 10% de probabilidad (1/10).\n"
            "- Debes estimar la probabilidad real basándote en {players_report}, {tournament_report}, {weather_report}, {news_report}, {sentiment_report} y {match_live_report}.\n"
            "- Debes comprobar si la probabilidad real supera el umbral de rentabilidad de la odd.\n"
            "- Debes concluir qué sugieren estas odds y cómo repercute eso en el resultado del set.\n"
            "- Si encuentras valor positivo, sugiere porcentaje del saldo usando Kelly fraccional 0.25-0.5; si no, sugiere 0%.\n\n"
            "ARGUMENTOS PREVIOS A REBATIR DESDE LA VISIÓN PROBABILÍSTICA:\n"
            "- Analista Agresivo: {current_aggressive_response}\n"
            "- Analista Neutral: {current_neutral_response}\n"
            "- Analista Seguro: {current_safe_response}\n\n"
            "HISTORIAL DE DEBATE:\n"
            "{history}\n\n"
            "REQUISITOS DE RESPUESTA NO NEGOCIABLES:\n"
            "- Responde de forma conversacional.\n"
            "- Analiza y relaciona las odds disponibles comparando probabilidades implícitas vs reales.\n"
            "- Identifica cuál odd, si alguna, tiene valor esperado positivo y si la probabilidad real supera el umbral de rentabilidad.\n"
            "- Si encuentras valor positivo, sugiere % del saldo; si no, sugiere 0%.\n"
            "- Cuestiona los argumentos previos con visión probabilística, sin formato especial.\n"
            "- No inventes datos. Sé directo sobre rentabilidad matemática a largo plazo."
        )

        prompt = PromptBuilder.create_debator_prompt(
            anatomy=anatomy,
            additional_context=additional_context,
        )

        prompt = prompt.partial(player_of_interest=player_of_interest)
        prompt = prompt.partial(opponent=opponent)
        prompt = prompt.partial(tournament=tournament)
        prompt = prompt.partial(match_date=match_date)
        prompt = prompt.partial(wallet_balance=wallet_balance)
        prompt = prompt.partial(odds_report=odds_report)
        prompt = prompt.partial(players_report=players_report)
        prompt = prompt.partial(tournament_report=tournament_report)
        prompt = prompt.partial(weather_report=weather_report)
        prompt = prompt.partial(news_report=news_report)
        prompt = prompt.partial(sentiment_report=sentiment_report)
        prompt = prompt.partial(match_live_report=match_live_report)
        prompt = prompt.partial(current_aggressive_response=current_aggressive_response)
        prompt = prompt.partial(current_neutral_response=current_neutral_response)
        prompt = prompt.partial(current_safe_response=current_safe_response)
        prompt = prompt.partial(history=history)

        chain = prompt | llm

        input_data = {
            "user_message": (
                f"Evalúa el valor esperado para {player_of_interest} vs {opponent}. "
                "Compara probabilidades implícitas y reales, identifica EV+ si existe y rebate al resto desde una visión probabilística."
            )
        }

        response = chain.invoke(input_data)

        argument = f"Expected Value Analyst: {response.content}"

        new_risk_debate_state = {
            HISTORYS.history: history + "\n" + argument,
            HISTORYS.aggressive_history: risk_debate_state.get(HISTORYS.aggressive_history, ""),
            HISTORYS.safe_history: risk_debate_state.get(HISTORYS.safe_history, ""),
            HISTORYS.neutral_history: risk_debate_state.get(HISTORYS.neutral_history, ""),
            HISTORYS.expected_history: expected_history + "\n" + argument,
            STATE.latest_speaker: SPEAKERS.expected,
            RESPONSES.aggressive: risk_debate_state.get(RESPONSES.aggressive, ""),
            RESPONSES.safe: risk_debate_state.get(RESPONSES.safe, ""),
            RESPONSES.neutral: risk_debate_state.get(RESPONSES.neutral, ""),
            RESPONSES.expected: argument,
            STATE.count: risk_debate_state.get(STATE.count, 0) + 1,
        }

        return {STATE.risk_debate_state: new_risk_debate_state}

    return expected_node
