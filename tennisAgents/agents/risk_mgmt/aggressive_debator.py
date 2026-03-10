from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, RiskDebatorAnatomies


def create_aggressive_debator(llm):
    def aggressive_node(state) -> dict:
        risk_debate_state = state[STATE.risk_debate_state]
        history = risk_debate_state.get(HISTORYS.history, "")
        aggressive_history = risk_debate_state.get(HISTORYS.aggressive_history, "")

        current_neutral_response = risk_debate_state.get(RESPONSES.neutral, "")
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

        anatomy = RiskDebatorAnatomies.aggressive_debator()

        additional_context = (
            "INFORMACIÓN DEL USUARIO Y PARTIDO:\n"
            "- Fecha del partido: {match_date}\n"
            "- Jugador de interés: {player_of_interest}\n"
            "- Oponente: {opponent}\n"
            "- Torneo: {tournament}\n"
            "- Saldo disponible: ${wallet_balance}\n\n"
            "DETALLES OBLIGATORIOS DE LA TAREA:\n"
            "- Debes construir tu razonamiento a partir de los reportes disponibles, sin depender de una plantilla fija de factores.\n"
            "- Debes estudiar las cuotas de apuestas disponibles y sus probabilidades implícitas.\n"
            "- Debes contrastar la evidencia de los reportes con el mercado para detectar incoherencias que puedan ser oportunidades de inversión.\n"
            "- Si una cuota tiene mayor probabilidad real de suceder que la probabilidad implícita de la casa, puedes tratarla como oportunidad potencial, siempre justificándolo.\n"
            "- La estrategia de inversión debe ser rentable matemáticamente y en el tiempo; si no existe oportunidad, debes decir explícitamente que no se apuesta.\n"
            "- No estás obligado a predecir un marcador exacto del set si la evidencia no lo sostiene con claridad.\n\n"
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
            "- Analista neutral: {current_neutral_response}\n"
            "- Analista de probabilidades: {current_expected_response}\n\n"
            "HISTORIAL DE DEBATE:\n"
            "{history}\n\n"
            "REQUISITOS DE RESPUESTA NO NEGOCIABLES:\n"
            "- Selecciona libremente los factores que consideres más relevantes según la evidencia disponible.\n"
            "- Explica tu estrategia de inversión agresiva para las cuotas o el mercado analizado.\n"
            "- Justifica matemáticamente por qué tomar riesgos tiene sentido dadas las circunstancias.\n"
            "- Rebate directamente los argumentos de los analistas conservador y neutral.\n"
            "- Si no hay una oportunidad agresiva con base suficiente, dilo explícitamente.\n"
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
        prompt = prompt.partial(current_neutral_response=current_neutral_response)
        prompt = prompt.partial(current_expected_response=current_expected_response)
        prompt = prompt.partial(history=history)

        chain = prompt | llm

        input_data = {
            "user_message": (
                f"Defiende la postura agresiva para {player_of_interest} vs {opponent}. "
                "Analiza la evidencia disponible, las cuotas y una estrategia agresiva sin caer en inversiones contradictorias."
            )
        }

        response = chain.invoke(input_data)

        argument = f"Aggressive Analyst: {response.content}"

        new_risk_debate_state = {
            HISTORYS.history: history + "\n" + argument,
            HISTORYS.aggressive_history: aggressive_history + "\n" + argument,
            HISTORYS.safe_history: risk_debate_state.get(HISTORYS.safe_history, ""),
            HISTORYS.neutral_history: risk_debate_state.get(HISTORYS.neutral_history, ""),
            HISTORYS.expected_history: risk_debate_state.get(HISTORYS.expected_history, ""),
            STATE.latest_speaker: SPEAKERS.aggressive,
            RESPONSES.aggressive: argument,
            RESPONSES.neutral: risk_debate_state.get(RESPONSES.neutral, ""),
            RESPONSES.safe: risk_debate_state.get(RESPONSES.safe, ""),
            RESPONSES.expected: risk_debate_state.get(RESPONSES.expected, ""),
            STATE.count: risk_debate_state.get(STATE.count, 0) + 1,
        }

        return {STATE.risk_debate_state: new_risk_debate_state}

    return aggressive_node
