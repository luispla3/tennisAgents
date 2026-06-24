from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import Dict

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

from tennisAgents.agents.analysts.news import create_news_analyst
from tennisAgents.agents.analysts.odds import create_odds_analyst
from tennisAgents.agents.analysts.players import create_player_analyst
from tennisAgents.agents.analysts.social_media import create_social_media_analyst
from tennisAgents.agents.analysts.tournament import create_tournament_analyst
from tennisAgents.agents.analysts.weather import create_weather_analyst
from tennisAgents.agents.analysts.match_live import create_match_live_analyst
from tennisAgents.agents.generalist import GENERALIST_NODE, create_generalist_llm

from tennisAgents.agents.utils.agent_states import AgentState
from tennisAgents.agents.utils.agent_utils import Toolkit, create_msg_delete
from tennisAgents.dataflows.config import get_config
from tennisAgents.utils.enumerations import *

from .conditional_logic import ConditionalLogic

REPORT_KEYS = [
    REPORTS.news_report,
    REPORTS.odds_report,
    REPORTS.players_report,
    REPORTS.sentiment_report,
    REPORTS.tournament_report,
    REPORTS.weather_report,
    REPORTS.match_live_report,
]


def _emit_progress(event: dict) -> None:
    """Emite eventos de progreso al callback configurado."""
    callback = get_config().get("progress_callback")
    if callback:
        try:
            callback(event)
        except Exception:
            pass


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
        toolkit: Toolkit,
        tool_nodes: Dict[str, ToolNode],
        conditional_logic: ConditionalLogic,
        local_llm: ChatOpenAI = None,
    ):
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.toolkit = toolkit
        self.tool_nodes = tool_nodes
        self.conditional_logic = conditional_logic
        self.local_llm = local_llm or quick_thinking_llm

    def _build_analyst_subgraph(self, analyst_type, analyst_node, delete_node, tool_node, conditional_fn):
        """Construye el subgrafo de un analista individual con sus tools y limpieza de mensajes."""
        workflow = StateGraph(AgentState)
        analyst_name = f"{analyst_type.capitalize()} Analyst"
        clear_name = f"Msg Clear {analyst_type.capitalize()}"
        tools_name = f"tools_{analyst_type}"

        workflow.add_node(analyst_name, analyst_node)
        workflow.add_node(clear_name, delete_node)
        if tool_node is not None:
            workflow.add_node(tools_name, tool_node)

        workflow.add_edge(START, analyst_name)
        if tool_node is not None:
            workflow.add_conditional_edges(
                analyst_name,
                conditional_fn,
                [tools_name, clear_name],
            )
            workflow.add_edge(tools_name, analyst_name)
        else:
            workflow.add_edge(analyst_name, clear_name)
        workflow.add_edge(clear_name, END)
        return workflow.compile()

    def _create_parallel_analysts_node(self, analyst_subgraphs, selected_analysts):
        """Crea el nodo que ejecuta todos los analistas seleccionados en paralelo."""
        analyst_recursion_limit = 24

        def parallel_analysts_node(state):
            """Ejecuta los subgrafos de analistas en paralelo y fusiona sus informes."""
            print(f"\n{'=' * 80}", flush=True)
            print(f"EJECUTANDO {len(selected_analysts)} ANALISTAS EN PARALELO", flush=True)
            print(f"Analistas: {', '.join(selected_analysts)}", flush=True)
            print(f"{'=' * 80}\n", flush=True)
            _emit_progress({"type": "parallel_start", "analysts": list(selected_analysts)})
            for analyst_type in selected_analysts:
                _emit_progress({"type": "analyst_start", "analyst": analyst_type})

            running = set(selected_analysts)
            running_lock = threading.Lock()
            stop_heartbeat = threading.Event()

            def heartbeat():
                while not stop_heartbeat.wait(12):
                    with running_lock:
                        still_running = sorted(running)
                    if still_running:
                        _emit_progress(
                            {"type": "analysts_running", "analysts": still_running}
                        )

            heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
            heartbeat_thread.start()

            def run_analyst(analyst_type):
                print(f"▶ Iniciando analista '{analyst_type}'...", flush=True)
                subgraph = analyst_subgraphs[analyst_type]
                local_state = dict(state)
                local_state[STATE.messages] = [HumanMessage(content="Continue")]
                try:
                    result = subgraph.invoke(
                        local_state,
                        config={"recursion_limit": analyst_recursion_limit},
                    )
                    print(f"✓ Analista '{analyst_type}' completado", flush=True)
                    reports = {
                        key: result[key]
                        for key in REPORT_KEYS
                        if result.get(key)
                    }
                    _emit_progress(
                        {
                            "type": "analyst_complete",
                            "analyst": analyst_type,
                            "reports": reports,
                        }
                    )
                    return analyst_type, result
                except Exception as exc:
                    print(f"✗ Error en analista '{analyst_type}': {exc}", flush=True)
                    _emit_progress(
                        {"type": "analyst_error", "analyst": analyst_type, "error": str(exc)}
                    )
                    return analyst_type, {}
                finally:
                    with running_lock:
                        running.discard(analyst_type)

            merged = {}
            try:
                with ThreadPoolExecutor(max_workers=len(selected_analysts)) as executor:
                    futures = {
                        executor.submit(run_analyst, analyst_type): analyst_type
                        for analyst_type in selected_analysts
                    }
                    for future in as_completed(futures):
                        analyst_type = futures[future]
                        try:
                            completed_type, result = future.result(timeout=900)
                        except Exception as exc:
                            print(f"✗ Timeout/error esperando '{analyst_type}': {exc}", flush=True)
                            with running_lock:
                                running.discard(analyst_type)
                            continue
                        for key in REPORT_KEYS:
                            value = result.get(key)
                            if value:
                                merged[key] = value
            finally:
                stop_heartbeat.set()
                heartbeat_thread.join(timeout=1)

            print(f"\n{'=' * 80}", flush=True)
            print(
                f"ANALISTAS FINALIZADOS: {sum(1 for k in REPORT_KEYS if merged.get(k))}/{len(selected_analysts)}",
                flush=True,
            )
            print(f"{'=' * 80}\n", flush=True)
            _emit_progress(
                {
                    "type": "parallel_complete",
                    "completed": sum(1 for k in REPORT_KEYS if merged.get(k)),
                    "total": len(selected_analysts),
                }
            )

            merged[STATE.messages] = [HumanMessage(content="Continue")]
            return merged

        return parallel_analysts_node

    def setup_graph(
        self, selected_analysts=[ANALYST_NODES.news, ANALYST_NODES.players, ANALYST_NODES.social, ANALYST_NODES.tournament, ANALYST_NODES.weather, ANALYST_NODES.match_live, ANALYST_NODES.odds]
    ):
        """Configura y compila el grafo: analistas en paralelo seguidos del generalista."""
        if len(selected_analysts) == 0:
            raise ValueError("Tennis Agents Graph Setup Error: no analysts selected!")

        analyst_nodes = {}
        delete_nodes = {}
        tool_nodes_map = {}

        if "news" in selected_analysts:
            analyst_nodes["news"] = create_news_analyst(self.quick_thinking_llm, self.toolkit)
            delete_nodes["news"] = create_msg_delete()
            tool_nodes_map["news"] = None

        if "odds" in selected_analysts:
            analyst_nodes["odds"] = create_odds_analyst(self.quick_thinking_llm, self.toolkit)
            delete_nodes["odds"] = create_msg_delete()
            tool_nodes_map["odds"] = self.tool_nodes.get("odds")

        if "players" in selected_analysts:
            analyst_nodes["players"] = create_player_analyst(self.quick_thinking_llm, self.toolkit)
            delete_nodes["players"] = create_msg_delete()
            tool_nodes_map["players"] = self.tool_nodes.get("players")

        if "social" in selected_analysts:
            analyst_nodes["social"] = create_social_media_analyst(self.local_llm, self.toolkit)
            delete_nodes["social"] = create_msg_delete()
            tool_nodes_map["social"] = self.tool_nodes.get("social")

        if "tournament" in selected_analysts:
            analyst_nodes["tournament"] = create_tournament_analyst(self.local_llm, self.toolkit)
            delete_nodes["tournament"] = create_msg_delete()
            tool_nodes_map["tournament"] = self.tool_nodes.get("tournament")

        if "weather" in selected_analysts:
            analyst_nodes["weather"] = create_weather_analyst(self.local_llm, self.toolkit)
            delete_nodes["weather"] = create_msg_delete()
            tool_nodes_map["weather"] = self.tool_nodes.get("weather")

        if "match_live" in selected_analysts:
            analyst_nodes["match_live"] = create_match_live_analyst(self.quick_thinking_llm, self.toolkit)
            delete_nodes["match_live"] = create_msg_delete()
            tool_nodes_map["match_live"] = self.tool_nodes.get("match_live")

        analyst_subgraphs = {}
        for analyst_type in selected_analysts:
            conditional_fn = getattr(self.conditional_logic, f"should_continue_{analyst_type}")
            analyst_subgraphs[analyst_type] = self._build_analyst_subgraph(
                analyst_type,
                analyst_nodes[analyst_type],
                delete_nodes[analyst_type],
                tool_nodes_map.get(analyst_type),
                conditional_fn,
            )

        generalist_node = create_generalist_llm(self.deep_thinking_llm)
        parallel_analysts_node = self._create_parallel_analysts_node(analyst_subgraphs, selected_analysts)

        workflow = StateGraph(AgentState)
        workflow.add_node("Parallel Analysts", parallel_analysts_node)
        workflow.add_node(GENERALIST_NODE, generalist_node)

        workflow.add_edge(START, "Parallel Analysts")
        workflow.add_edge("Parallel Analysts", GENERALIST_NODE)
        workflow.add_edge(GENERALIST_NODE, END)

        return workflow.compile()
