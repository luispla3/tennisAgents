from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage, RemoveMessage
from typing import Annotated
from langchain_core.tools import tool
from datetime import datetime
from tradingagents.default_config import DEFAULT_CONFIG
import tradingagents.dataflows.interface as interface


def create_msg_delete():
    def delete_messages(state):
        messages = state["messages"]
        removal_ops = [RemoveMessage(id=m.id) for m in messages]
        placeholder = HumanMessage(content="Continue")
        return {"messages": removal_ops + [placeholder]}

    return delete_messages


class Toolkit:
    _config = DEFAULT_CONFIG.copy()

    @classmethod
    def update_config(cls, config):
        cls._config.update(config)

    @property
    def config(self):
        return self._config

    def __init__(self, config=None):
        if config:
            self.update_config(config)

    @staticmethod
    @tool
    def get_reddit_news(curr_date: Annotated[str, "yyyy-mm-dd"]):
        return interface.get_reddit_global_news(curr_date, 7, 5)

    @staticmethod
    @tool
    def get_finnhub_news(ticker: Annotated[str, "e.g. AAPL"], start_date: Annotated[str, "yyyy-mm-dd"], end_date: Annotated[str, "yyyy-mm-dd"]):
        look_back_days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days
        return interface.get_finnhub_news(ticker, end_date, look_back_days)

    @staticmethod
    @tool
    def get_reddit_stock_info(ticker: Annotated[str, "e.g. AAPL"], curr_date: Annotated[str, "yyyy-mm-dd"]):
        return interface.get_reddit_company_news(ticker, curr_date, 7, 5)

    @staticmethod
    @tool
    def get_YFin_data(symbol: Annotated[str, "e.g. AAPL"], start_date: Annotated[str, "yyyy-mm-dd"], end_date: Annotated[str, "yyyy-mm-dd"]):
        return interface.get_YFin_data(symbol, start_date, end_date)

    @staticmethod
    @tool
    def get_YFin_data_online(symbol: Annotated[str, "e.g. AAPL"], start_date: Annotated[str, "yyyy-mm-dd"], end_date: Annotated[str, "yyyy-mm-dd"]):
        return interface.get_YFin_data_online(symbol, start_date, end_date)

    @staticmethod
    @tool
    def get_stockstats_indicators_report(symbol: Annotated[str, "e.g. AAPL"], indicator: Annotated[str, "technical indicator"], curr_date: Annotated[str, "yyyy-mm-dd"], look_back_days: Annotated[int, "default 30"] = 30):
        return interface.get_stock_stats_indicators_window(symbol, indicator, curr_date, look_back_days, False)

    @staticmethod
    @tool
    def get_stockstats_indicators_report_online(symbol: Annotated[str, "e.g. AAPL"], indicator: Annotated[str, "technical indicator"], curr_date: Annotated[str, "yyyy-mm-dd"], look_back_days: Annotated[int, "default 30"] = 30):
        return interface.get_stock_stats_indicators_window(symbol, indicator, curr_date, look_back_days, True)

    @staticmethod
    @tool
    def get_finnhub_company_insider_sentiment(ticker: Annotated[str, "e.g. AAPL"], curr_date: Annotated[str, "yyyy-mm-dd"]):
        return interface.get_finnhub_company_insider_sentiment(ticker, curr_date, 30)

    @staticmethod
    @tool
    def get_finnhub_company_insider_transactions(ticker: Annotated[str, "e.g. AAPL"], curr_date: Annotated[str, "yyyy-mm-dd"]):
        return interface.get_finnhub_company_insider_transactions(ticker, curr_date, 30)

    @staticmethod
    @tool
    def get_simfin_balance_sheet(ticker: Annotated[str, "e.g. AAPL"], freq: Annotated[str, "annual/quarterly"], curr_date: Annotated[str, "yyyy-mm-dd"]):
        return interface.get_simfin_balance_sheet(ticker, freq, curr_date)

    @staticmethod
    @tool
    def get_simfin_cashflow(ticker: Annotated[str, "e.g. AAPL"], freq: Annotated[str, "annual/quarterly"], curr_date: Annotated[str, "yyyy-mm-dd"]):
        return interface.get_simfin_cashflow(ticker, freq, curr_date)

    @staticmethod
    @tool
    def get_simfin_income_stmt(ticker: Annotated[str, "e.g. AAPL"], freq: Annotated[str, "annual/quarterly"], curr_date: Annotated[str, "yyyy-mm-dd"]):
        return interface.get_simfin_income_statements(ticker, freq, curr_date)

    @staticmethod
    @tool
    def get_google_news(query: Annotated[str, "search query"], curr_date: Annotated[str, "yyyy-mm-dd"]):
        return interface.get_google_news(query, curr_date, 7)

    @staticmethod
    @tool
    def get_stock_news_openai(ticker: Annotated[str, "e.g. AAPL"], curr_date: Annotated[str, "yyyy-mm-dd"]):
        return interface.get_stock_news_openai(ticker, curr_date)

    @staticmethod
    @tool
    def get_global_news_openai(curr_date: Annotated[str, "yyyy-mm-dd"]):
        return interface.get_global_news_openai(curr_date)

    @staticmethod
    @tool
    def get_fundamentals_openai(ticker: Annotated[str, "e.g. AAPL"], curr_date: Annotated[str, "yyyy-mm-dd"]):
        return interface.get_fundamentals_openai(ticker, curr_date)
