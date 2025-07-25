from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

from tennisAgents.agents.analysts.news import create_news_analyst
from tennisAgents.agents.analysts.odds import create_odds_analyst
from tennisAgents.agents.analysts.players import create_players_analyst
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
        self, selected_analysts=["news", "odds", "players", "social_media", "tournament", "weather"]
    ):
        if len(selected_analysts) == 0:
            raise ValueError("Tennis Agents Graph Setup Error: no analysts selected!")

        analyst_nodes = {}
        delete_nodes = {}
        tool_nodes = {}

        if "news" in selected_analysts:
            analyst_nodes["news"] = create_news_analyst(self.quick_thinking_llm)
            delete_nodes["news"] = create_msg_delete()
            tool_nodes["news"] = self.tool_nodes.get("news")

        if "odds" in selected_analysts:
            analyst_nodes["odds"] = create_odds_analyst(self.quick_thinking_llm)
            delete_nodes["odds"] = create_msg_delete()
            tool_nodes["odds"] = self.tool_nodes.get("odds")

        if "players" in selected_analysts:
            analyst_nodes["players"] = create_players_analyst(self.quick_thinking_llm)
            delete_nodes["players"] = create_msg_delete()
            tool_nodes["players"] = self.tool_nodes.get("players")

        if "social_media" in selected_analysts:
            analyst_nodes["social_media"] = create_social_media_analyst(self.quick_thinking_llm)
            delete_nodes["social_media"] = create_msg_delete()
            tool_nodes["social_media"] = self.tool_nodes.get("social_media")

        if "tournament" in selected_analysts:
            analyst_nodes["tournament"] = create_tournament_analyst(self.quick_thinking_llm)
            delete_nodes["tournament"] = create_msg_delete()
            tool_nodes["tournament"] = self.tool_nodes.get("tournament")

        if "weather" in selected_analysts:
            analyst_nodes["weather"] = create_weather_analyst(self.quick_thinking_llm)
            delete_nodes["weather"] = create_msg_delete()
            tool_nodes["weather"] = self.tool_nodes.get("weather")

        aggressive_debator = create_aggressive_debator(self.quick_thinking_llm)
        conservative_debator = create_conservative_debator(self.quick_thinking_llm)
        expected_debator = create_expected_debator(self.quick_thinking_llm)
        neutral_debator = create_neutral_debator(self.quick_thinking_llm)
        risk_manager_node = create_risk_manager(self.deep_thinking_llm, self.risk_manager_memory)

        workflow = StateGraph(AgentState)

        for analyst_type, node in analyst_nodes.items():
            workflow.add_node(f"{analyst_type.capitalize()} Analyst", node)
            workflow.add_node(f"Msg Clear {analyst_type.capitalize()}", delete_nodes[analyst_type])
            workflow.add_node(f"tools_{analyst_type}", tool_nodes[analyst_type])

        workflow.add_node("Aggressive Debator", aggressive_debator)
        workflow.add_node("Conservative Debator", conservative_debator)
        workflow.add_node("Expected Debator", expected_debator)
        workflow.add_node("Neutral Debator", neutral_debator)
        workflow.add_node("Risk Judge", risk_manager_node)

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
                workflow.add_edge(current_clear, "Aggressive Debator")

        workflow.add_conditional_edges(
            "Aggressive Debator",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Conservative Debator": "Conservative Debator",
                "Expected Debator": "Expected Debator",
                "Neutral Debator": "Neutral Debator",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Conservative Debator",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Aggressive Debator": "Aggressive Debator",
                "Expected Debator": "Expected Debator",
                "Neutral Debator": "Neutral Debator",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Expected Debator",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Aggressive Debator": "Aggressive Debator",
                "Conservative Debator": "Conservative Debator",
                "Neutral Debator": "Neutral Debator",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Neutral Debator",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Aggressive Debator": "Aggressive Debator",
                "Conservative Debator": "Conservative Debator",
                "Expected Debator": "Expected Debator",
                "Risk Judge": "Risk Judge",
            },
        )

        workflow.add_edge("Risk Judge", END)

        return workflow.compile()