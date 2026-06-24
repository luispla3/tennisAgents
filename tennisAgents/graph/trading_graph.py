import os
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.prebuilt import ToolNode

from tennisAgents.agents import *
from tennisAgents.default_config import DEFAULT_CONFIG
from tennisAgents.dataflows.config import set_config
from tennisAgents.utils.enumerations import *

from .conditional_logic import ConditionalLogic
from .setup import GraphSetup
from .propagation import Propagator
from .reflection import Reflector
from .signal_processing import SignalProcessor


class TennisAgentsGraph:
    """Orquesta principal del sistema de agentes para apuestas de tenis."""

    def __init__(
        self,
        selected_analysts=["news", "players", "social", "tournament", "weather", "match_live", "odds"],
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
            llm_kwargs = {"base_url": self.config["backend_url"]}
            if self.config["llm_provider"].lower() == "openrouter":
                openrouter_api_key = self.config.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
                llm_kwargs["api_key"] = openrouter_api_key
                llm_kwargs["default_headers"] = {
                    "HTTP-Referer": "https://github.com/tennisAgents",
                    "X-Title": "Tennis Agents",
                }
            self.deep_thinking_llm = ChatOpenAI(model=self.config["deep_think_llm"], **llm_kwargs)
            self.quick_thinking_llm = ChatOpenAI(model=self.config["quick_think_llm"], **llm_kwargs)
        elif self.config["llm_provider"].lower() == "anthropic":
            self.deep_thinking_llm = ChatAnthropic(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = ChatAnthropic(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
        elif self.config["llm_provider"].lower() == "google":
            self.deep_thinking_llm = ChatGoogleGenerativeAI(model=self.config["deep_think_llm"])
            self.quick_thinking_llm = ChatGoogleGenerativeAI(model=self.config["quick_think_llm"])
        else:
            raise ValueError(f"Proveedor LLM no soportado: {self.config['llm_provider']}")

        # Inicializar LLM local (Ollama) o OpenRouter para analistas específicos (News, Social, Tournament, Weather)
        self.local_llm = None
        if self.config.get("use_local_analysts", False):
            try:
                local_base_url = self.config.get("local_base_url", "http://localhost:11434/v1")
                local_model = self.config.get("local_model_name", "qwen2.5:3b")
                
                # Detectar si es local (Ollama) o OpenRouter basado en la URL
                is_local = "localhost" in local_base_url or "127.0.0.1" in local_base_url
                
                if self.debug:
                    print(f"DEBUG: Analistas locales - URL: {local_base_url}, is_local: {is_local}")

                if is_local:
                    # Configuración para Ollama local (no requiere API key real)
                    base_url_cleaned = local_base_url.replace("/v1", "") if local_base_url.endswith("/v1") else local_base_url
                    self.local_llm = ChatOllama(
                        model=local_model,
                        base_url=base_url_cleaned,
                        temperature=0.1,
                        num_ctx=16384,
                        num_predict=4096,
                        reasoning=False
                    )
                    if self.debug:
                        print(f"✓ Ollama LLM local inicializado para analistas: {local_model}")
                        print(f"  Asegúrate de tener Ollama corriendo en {local_base_url}")
                else:
                    # Configuración para OpenRouter (requiere API key)
                    local_api_key = self.config.get("local_api_key") or os.getenv("OPENROUTER_API_KEY")
                    if local_api_key:
                        self.local_llm = ChatOpenAI(
                            model=local_model,
                            base_url=local_base_url,
                            api_key=local_api_key,
                            default_headers={
                                "HTTP-Referer": "https://github.com/tennisAgents",
                                "X-Title": "Tennis Agents"
                            },
                            temperature=0.7
                        )
                        if self.debug:
                            print(f"✓ OpenRouter LLM inicializado para analistas: {local_model}")
                    else:
                        if self.debug:
                            print(f"⚠ Warning: OPENROUTER_API_KEY no configurada. Los analistas usarán gpt-4o-mini.")
            except Exception as e:
                if self.debug:
                    print(f"⚠ Warning: No se pudo inicializar LLM para analistas: {e}")

        self.toolkit = Toolkit(config=self.config)

        self.tool_nodes = self._create_tool_nodes()

        self.conditional_logic = ConditionalLogic()
        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.toolkit,
            self.tool_nodes,
            self.conditional_logic,
            local_llm=self.local_llm,
        )

        self.propagator = Propagator()         #se usa en web/app.py para inicializar el estado inicial del grafo
        self.reflector = Reflector(self.quick_thinking_llm)                    #no se usa en ningun sitio
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)       #no se usa en web/app.py, solo en cli

        self.curr_state = None
        self.match = None
        self.log_states_dict = {}

        self.graph = self.graph_setup.setup_graph(selected_analysts)

    def _create_tool_nodes(self) -> Dict[str, ToolNode]:
        """Crea nodos de herramientas para cada analista especializado en tenis."""
        return {
            "news": ToolNode(
                [
                    self.toolkit.get_news,
                ]
            ),
            "odds": ToolNode(
                [
                    self.toolkit.get_betfair_odds_scraper,
                ]
            ),
            "players": ToolNode(
                [
                    self.toolkit.get_atp_rankings,
                    self.toolkit.get_recent_matches,
                    self.toolkit.get_surface_winrate,
                    self.toolkit.get_head_to_head,
                    self.toolkit.get_injury_reports,
                ]
            ),
            "sentiment": ToolNode(
                [
                    self.toolkit.get_sentiment,
                ]
            ),
            "social": ToolNode(
                [
                    self.toolkit.get_sentiment,
                ]
            ),
            "tournament": ToolNode(
                [
                    self.toolkit.get_tournament_info,
                ]
            ),
            "weather": ToolNode(
                [
                    self.toolkit.get_weather_forecast,
                ]
            ),
            "match_live": ToolNode(
                [
                    self.toolkit.get_match_live_data,
                ]
            ),
        }

    #ninguno de los siguientes metodos se usa en web/app.py

    def propagate(self, player_pair, match_date, tournament, wallet_balance):
        self.match = player_pair

        init_agent_state = self.propagator.create_initial_state(
            player_pair.split(" vs ")[0].strip(), 
            player_pair.split(" vs ")[1].strip(), 
            match_date,
            tournament,
            wallet_balance
        )
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
        STATE.match_date: final_state[STATE.match_date],
        STATE.player_of_interest: final_state[STATE.player_of_interest],
        STATE.opponent: final_state[STATE.opponent],
        STATE.tournament: final_state[STATE.tournament],
        STATE.wallet_balance: final_state[STATE.wallet_balance],
        STATE.messages: final_state[STATE.messages],
        "reports": {
            REPORTS.players_report: final_state.get(REPORTS.players_report, ""),
            REPORTS.news_report: final_state.get(REPORTS.news_report, ""),
            REPORTS.odds_report: final_state.get(REPORTS.odds_report, ""),
            REPORTS.sentiment_report: final_state.get(REPORTS.sentiment_report, ""),
            REPORTS.weather_report: final_state.get(REPORTS.weather_report, ""),
            REPORTS.tournament_report: final_state.get(REPORTS.tournament_report, ""),
            REPORTS.match_live_report: final_state.get(REPORTS.match_live_report, ""),
        },
        STATE.final_bet_decision: final_state.get(STATE.final_bet_decision, ""),
    }

        # Use configuration for results directory, fallback to 'results' in current working directory
        # We construct the path dynamically based on config to match web/app.py behavior if needed
        # But here we just want to log the full state JSON
        
        # If called from web app, config['results_dir'] might be absolute
        results_base = self.config.get("results_dir", "results")
        
        # If running from web/app.py, we want to save in the same folder structure
        # Construct path: results_dir / match_pair_timestamp / date
        
        # We need to find the specific match folder created. 
        # Since we don't have the timestamp here easily without passing it down,
        # we might create a new folder or try to find the latest one.
        # HOWEVER, web/app.py creates the directory structure.
        
        # Strategy: If results_dir is provided in config, use it as base.
        # If it's absolute, use it. If relative, make it relative to project root.
        
        base_path = Path(results_base)
        if not base_path.is_absolute():
            # Assuming running from project root or relative to it
            # If running from web/, we need to go up one level or similar?
            # self.config["project_dir"] usually holds project root
            project_root = Path(self.config.get("project_dir", os.getcwd()))
            base_path = project_root / results_base
            
        # Create a generic logs directory if we can't match the exact timestamped folder easily
        # OR, better: let the caller handle logging if they want precise location?
        # But this method is called internally.
        
        # Let's stick to a consistent location for logs:
        # eval_results/{match}/TennisAgents_logs/ is what was there.
        # Let's change it to match the config results dir structure if possible.
        
        # For now, to ensure it works as requested "inside results of web":
        # We'll use the base_path derived from config.
        
        # Note: This specific log file (full_states_log) is different from the reports.
        # The user asked for "reports" to be saved.
        
        # Let's keep this logging but fix the path to be inside the configured results dir
        # We'll create a 'logs' folder in the results base for now, or try to put it in the match folder
        
        # Using a simple timestamp for the log folder to avoid overwriting if called multiple times
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = base_path / "logs" / f"{self.match}_{timestamp}"
        log_dir.mkdir(parents=True, exist_ok=True)

        with open(
            log_dir / f"full_states_log_{match_date}.json",
            "w",
        ) as f:
            json.dump(self.log_states_dict, f, indent=4)

    def reflect_and_remember(self, returns):
        """Reflexiona sobre la decisión final y registra las lecciones aprendidas."""
        self.reflector.reflect_decision(self.curr_state, returns)

    def process_signal(self, full_signal):
        return self.signal_processor.process_signal(full_signal)