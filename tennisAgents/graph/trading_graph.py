import os
from pathlib import Path
import json
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.prebuilt import ToolNode

from tennisAgents.agents import *
from tennisAgents.default_config import DEFAULT_CONFIG
from tennisAgents.agents.utils.memory import TennisSituationMemory
from tennisAgents.agents.utils.agent_states import AgentState
from tennisAgents.dataflows.interface import set_config

from .conditional_logic import ConditionalLogic
#from .setup import GraphSetup
from .propagation import Propagator
from .reflection import Reflector
from .signal_processing import SignalProcessor


class TennisAgentsGraph:
    """Orquesta principal del sistema de agentes para apuestas de tenis."""

    def __init__(
        self,
        selected_analysts=["ranking", "forma", "clima", "head2head"],
        debug=False,
        config: Dict[str, Any] = None,
    ):
        self.debug = debug
        self.config = config or DEFAULT_CONFIG

        set_config(self.config)

        os.makedirs(
            os.path.join(self.config["project_dir"], "dataflows/data_cache"),
            exist_ok=True,
        )

        if self.config["llm_provider"].lower() in ["openai", "ollama", "openrouter"]:
            self.deep_thinking_llm = ChatOpenAI(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = ChatOpenAI(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
        elif self.config["llm_provider"].lower() == "anthropic":
            self.deep_thinking_llm = ChatAnthropic(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = ChatAnthropic(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
        elif self.config["llm_provider"].lower() == "google":
            self.deep_thinking_llm = ChatGoogleGenerativeAI(model=self.config["deep_think_llm"])
            self.quick_thinking_llm = ChatGoogleGenerativeAI(model=self.config["quick_think_llm"])
        else:
            raise ValueError(f"Proveedor LLM no soportado: {self.config['llm_provider']}")

        self.toolkit = Toolkit(config=self.config)

        self.risk_analyst_memory = TennisSituationMemory("risk_analyst_memory", self.config)

        self.tool_nodes = self._create_tool_nodes()

        self.conditional_logic = ConditionalLogic()
        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.toolkit,
            self.tool_nodes,
            self.risk_analyst_memory,
            self.conditional_logic,
        )

        self.propagator = Propagator()
        self.reflector = Reflector(self.quick_thinking_llm)
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)

        self.curr_state = None
        self.match = None
        self.log_states_dict = {}

        self.graph = self.graph_setup.setup_graph(selected_analysts)

    def _create_tool_nodes(self) -> Dict[str, ToolNode]:
        return {
            "ranking": ToolNode([
                self.toolkit.get_atp_ranking,
                self.toolkit.get_historical_performance,
            ]),
            "forma": ToolNode([
                self.toolkit.get_recent_match_stats,
            ]),
            "clima": ToolNode([
                self.toolkit.get_weather_conditions,
            ]),
            "head2head": ToolNode([
                self.toolkit.get_head2head_stats,
            ]),
        }

    def propagate(self, player_pair, match_date):
        self.match = player_pair

        init_agent_state = self.propagator.create_initial_state(player_pair, match_date)
        args = self.propagator.get_graph_args()

        if self.debug:
            trace = []
            for chunk in self.graph.stream(init_agent_state, **args):
                if chunk["messages"]:
                    chunk["messages"][-1].pretty_print()
                    trace.append(chunk)
            final_state = trace[-1]
        else:
            final_state = self.graph.invoke(init_agent_state, **args)

        self.curr_state = final_state
        self._log_state(match_date, final_state)

        return final_state, self.process_signal(final_state["final_bet_decision"])

    def _log_state(self, match_date, final_state):
        self.log_states_dict[str(match_date)] = {
            "match": final_state["match"],
            "match_date": final_state["match_date"],
            "ranking_report": final_state["ranking_report"],
            "form_report": final_state["form_report"],
            "weather_report": final_state["weather_report"],
            "head2head_report": final_state["head2head_report"],
            "strategy_debate_state": final_state["strategy_debate_state"],
            "risk_debate_state": final_state["risk_debate_state"],
            "bet_strategy": final_state["bet_strategy"],
            "final_bet_decision": final_state["final_bet_decision"],
        }

        directory = Path(f"eval_results/{self.match}/TennisAgents_logs/")
        directory.mkdir(parents=True, exist_ok=True)

        with open(
            f"eval_results/{self.match}/TennisAgents_logs/full_states_log_{match_date}.json",
            "w",
        ) as f:
            json.dump(self.log_states_dict, f, indent=4)

    def reflect_and_remember(self, returns):
        self.reflector.reflect_risk_manager(
            self.curr_state, returns, self.risk_analyst_memory
        )

    def process_signal(self, full_signal):
        return self.signal_processor.process_signal(full_signal)
