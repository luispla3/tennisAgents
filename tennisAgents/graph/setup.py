from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

from tennisAgents.agents.analysts.news import create_news_analyst
from tennisAgents.agents.analysts.odds import create_odds_analyst
from tennisAgents.agents.analysts.players import create_player_analyst
from tennisAgents.agents.analysts.social_media import create_social_media_analyst
from tennisAgents.agents.analysts.tournament import create_tournament_analyst
from tennisAgents.agents.analysts.weather import create_weather_analyst

from tennisAgents.agents.managers.manager import create_risk_manager

from tennisAgents.agents.risk_mgmt.aggressive_debator import create_aggressive_debator
from tennisAgents.agents.risk_mgmt.conservative_debator import create_conservative_debator
from tennisAgents.agents.risk_mgmt.expected_debator import create_expected_debator
from tennisAgents.agents.risk_mgmt.neutral_debator import create_neutral_debator
from tennisAgents.agents.utils.agent_states import AgentState
from tennisAgents.agents.utils.agent_utils import Toolkit, create_msg_delete
from tennisAgents.utils.enumerations import *

from .conditional_logic import ConditionalLogic

class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
        toolkit: Toolkit,
        tool_nodes: Dict[str, ToolNode],
        risk_manager_memory,
        conditional_logic: ConditionalLogic,
    ):
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.toolkit = toolkit
        self.tool_nodes = tool_nodes
        self.risk_manager_memory = risk_manager_memory
        self.conditional_logic = conditional_logic

    def setup_graph(
        self, selected_analysts=[ANALYST_NODES.news, ANALYST_NODES.odds, ANALYST_NODES.players, ANALYST_NODES.social, ANALYST_NODES.tournament, ANALYST_NODES.weather]
    ):
        if len(selected_analysts) == 0:
            raise ValueError("Tennis Agents Graph Setup Error: no analysts selected!")

        analyst_nodes = {}
        delete_nodes = {}
        tool_nodes = {}

        if ANALYST_NODES.news in selected_analysts:
            analyst_nodes[ANALYST_NODES.news] = create_news_analyst(self.quick_thinking_llm)
            delete_nodes[ANALYST_NODES.news] = create_msg_delete()
            tool_nodes[ANALYST_NODES.news] = self.tool_nodes.get(ANALYST_NODES.news)

        if ANALYST_NODES.odds in selected_analysts:
            analyst_nodes[ANALYST_NODES.odds] = create_odds_analyst(self.quick_thinking_llm)
            delete_nodes[ANALYST_NODES.odds] = create_msg_delete()
            tool_nodes[ANALYST_NODES.odds] = self.tool_nodes.get(ANALYST_NODES.odds)

        if ANALYST_NODES.players in selected_analysts:
            analyst_nodes[ANALYST_NODES.players] = create_player_analyst(self.quick_thinking_llm)
            delete_nodes[ANALYST_NODES.players] = create_msg_delete()
            tool_nodes[ANALYST_NODES.players] = self.tool_nodes.get(ANALYST_NODES.players)

        if ANALYST_NODES.social in selected_analysts:
            analyst_nodes[ANALYST_NODES.social] = create_social_media_analyst(self.quick_thinking_llm)
            delete_nodes[ANALYST_NODES.social] = create_msg_delete()
            tool_nodes[ANALYST_NODES.social] = self.tool_nodes.get(ANALYST_NODES.social)

        if ANALYST_NODES.tournament in selected_analysts:
            analyst_nodes[ANALYST_NODES.tournament] = create_tournament_analyst(self.quick_thinking_llm)
            delete_nodes[ANALYST_NODES.tournament] = create_msg_delete()
            tool_nodes[ANALYST_NODES.tournament] = self.tool_nodes.get(ANALYST_NODES.tournament)

        if ANALYST_NODES.weather in selected_analysts:
            analyst_nodes[ANALYST_NODES.weather] = create_weather_analyst(self.quick_thinking_llm)
            delete_nodes[ANALYST_NODES.weather] = create_msg_delete()
            tool_nodes[ANALYST_NODES.weather] = self.tool_nodes.get(ANALYST_NODES.weather)

        aggressive_debator = create_aggressive_debator(self.quick_thinking_llm)
        safe_debator = create_conservative_debator(self.quick_thinking_llm)
        expected_debator = create_expected_debator(self.quick_thinking_llm)
        neutral_debator = create_neutral_debator(self.quick_thinking_llm)
        risk_manager_node = create_risk_manager(self.deep_thinking_llm, self.risk_manager_memory)

        workflow = StateGraph(AgentState)

        for analyst_type, node in analyst_nodes.items():
            workflow.add_node(f"{analyst_type.capitalize()} Analyst", node)
            workflow.add_node(f"Msg Clear {analyst_type.capitalize()}", delete_nodes[analyst_type])
            workflow.add_node(f"tools_{analyst_type}", tool_nodes[analyst_type])

        workflow.add_node(ANALYSTS.aggressive, aggressive_debator)
        workflow.add_node(ANALYSTS.safe, safe_debator)
        workflow.add_node(ANALYSTS.expected, expected_debator)
        workflow.add_node(ANALYSTS.neutral, neutral_debator)
        workflow.add_node(ANALYSTS.judge, risk_manager_node)

        first_analyst = selected_analysts[0]
        workflow.add_edge(START, f"{first_analyst.capitalize()} Analyst")

        for i, analyst_type in enumerate(selected_analysts):
            current_analyst = f"{analyst_type.capitalize()} Analyst"
            current_tools = f"tools_{analyst_type}"
            current_clear = f"Msg Clear {analyst_type.capitalize()}"

            workflow.add_conditional_edges(
                current_analyst,
                getattr(self.conditional_logic, f"should_continue_{analyst_type}", lambda x: True),
                [current_tools, current_clear],
            )
            workflow.add_edge(current_tools, current_analyst)

            if i < len(selected_analysts) - 1:
                next_analyst = f"{selected_analysts[i+1].capitalize()} Analyst"
                workflow.add_edge(current_clear, next_analyst)
            else:
                workflow.add_edge(current_clear, ANALYSTS.aggressive)

        workflow.add_conditional_edges(
            ANALYSTS.aggressive,
            self.conditional_logic.should_continue_risk_analysis,
            {
                ANALYSTS.safe: ANALYSTS.safe,
                ANALYSTS.expected: ANALYSTS.expected,
                ANALYSTS.neutral: ANALYSTS.neutral,
                ANALYSTS.judge: ANALYSTS.judge,
            },
        )
        workflow.add_conditional_edges(
            ANALYSTS.safe,
            self.conditional_logic.should_continue_risk_analysis,
            {
                ANALYSTS.aggressive: ANALYSTS.aggressive,
                ANALYSTS.expected: ANALYSTS.expected,
                ANALYSTS.neutral: ANALYSTS.neutral,
                ANALYSTS.judge: ANALYSTS.judge,
            },
        )
        workflow.add_conditional_edges(
            ANALYSTS.expected,
            self.conditional_logic.should_continue_risk_analysis,
            {
                ANALYSTS.aggressive: ANALYSTS.aggressive,
                ANALYSTS.safe: ANALYSTS.safe,
                ANALYSTS.neutral: ANALYSTS.neutral,
                ANALYSTS.judge: ANALYSTS.judge,
            },
        )
        workflow.add_conditional_edges(
            ANALYSTS.neutral,
            self.conditional_logic.should_continue_risk_analysis,
            {
                ANALYSTS.aggressive: ANALYSTS.aggressive,
                ANALYSTS.safe: ANALYSTS.safe,
                ANALYSTS.neutral: ANALYSTS.neutral,
                ANALYSTS.judge: ANALYSTS.judge,
            },
        )

        workflow.add_edge(ANALYSTS.judge, END)

        return workflow.compile()