import datetime
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.columns import Columns
from rich.layout import Layout
from rich.text import Text
from rich.live import Live
from rich.table import Table
from rich import box
from rich.align import Align

from cli.models import AnalystType
from cli.utils import get_players, get_tournament, get_date, select_analysts, select_research_depth, select_llm_provider, select_shallow_thinking_agent, select_deep_thinking_agent
from tennisAgents.graph.setup import TennisAgentsGraph
from tennisAgents.default_config import DEFAULT_CONFIG

console = Console()
app = typer.Typer(name="TennisAgents", help="TennisAgents CLI: Multi-Agents LLM Tennis Analysis Framework", add_completion=True)

class MessageBuffer:
    def __init__(self, max_length=100):
        self.messages = []
        self.tool_calls = []
        self.agent_status = {
            "News Analyst": "pending",
            "Odds Analyst": "pending",
            "Players Analyst": "pending",
            "Social Analyst": "pending",
            "Tournament Analyst": "pending",
            "Weather Analyst": "pending",
        }
        self.current_agent = None
        self.report_sections = {
            "players_report": None,
            "news_report": None,
            "odds_report": None,
            "social_report": None,
            "weather_report": None,
            "tournament_report": None,
            "final_bet_decision": None,
        }
        self.current_report = None
        self.final_report = None

    def add_message(self, message_type, content):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.messages.append((timestamp, message_type, content))

    def add_tool_call(self, tool_name, args):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.tool_calls.append((timestamp, tool_name, args))

    def update_agent_status(self, agent, status):
        if agent in self.agent_status:
            self.agent_status[agent] = status
            self.current_agent = agent

    def update_report_section(self, section_name, content):
        if section_name in self.report_sections:
            self.report_sections[section_name] = content
            self.current_report = f"### {section_name}\n{content}"

message_buffer = MessageBuffer()

def create_layout():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3),
    )
    layout["main"].split_column(
        Layout(name="upper", ratio=3), Layout(name="analysis", ratio=5)
    )
    layout["upper"].split_row(
        Layout(name="progress", ratio=2), Layout(name="messages", ratio=3)
    )
    return layout

def update_display(layout, spinner_text=None):
    layout["header"].update(
        Panel(
            "[bold green]Bienvenido a TennisAgents CLI[/bold green]\n"
            "[dim]© TennisAgents[/dim]",
            title="TennisAgents",
            border_style="green",
            padding=(1, 2),
            expand=True,
        )
    )

    progress_table = Table(
        show_header=True,
        header_style="bold magenta",
        box=box.SIMPLE_HEAD,
        expand=True,
    )
    progress_table.add_column("Analista", style="cyan", justify="center", width=20)
    progress_table.add_column("Estado", style="yellow", justify="center", width=20)

    for agent, status in message_buffer.agent_status.items():
        status_color = {
            "pending": "yellow",
            "completed": "green",
            "error": "red",
            "in_progress": "blue",
        }.get(status, "white")
        status_cell = f"[{status_color}]{status}[/{status_color}]"
        progress_table.add_row(agent, status_cell)

    layout["progress"].update(
        Panel(progress_table, title="Progreso", border_style="cyan", padding=(1, 2))
    )

    messages_table = Table(
        show_header=True,
        header_style="bold magenta",
        expand=True,
        box=box.MINIMAL,
        show_lines=True,
        padding=(0, 1),
    )
    messages_table.add_column("Hora", style="cyan", width=8, justify="center")
    messages_table.add_column("Tipo", style="green", width=10, justify="center")
    messages_table.add_column("Contenido", style="white", ratio=1)

    recent_messages = message_buffer.messages[-12:]
    for timestamp, msg_type, content in recent_messages:
        wrapped_content = Text(str(content), overflow="fold")
        messages_table.add_row(timestamp, msg_type, wrapped_content)

    if spinner_text:
        messages_table.add_row("", "Spinner", spinner_text)

    layout["messages"].update(
        Panel(
            messages_table,
            title="Mensajes & Herramientas",
            border_style="blue",
            padding=(1, 2),
        )
    )

    if message_buffer.current_report:
        layout["analysis"].update(
            Panel(
                Markdown(message_buffer.current_report),
                title="Reporte Actual",
                border_style="green",
                padding=(1, 2),
            )
        )
    else:
        layout["analysis"].update(
            Panel(
                "[italic]Esperando reporte de análisis...[/italic]",
                title="Reporte Actual",
                border_style="green",
                padding=(1, 2),
            )
        )

    stats_table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
    stats_table.add_column("Estadísticas", justify="center")
    stats_table.add_row(
        f"Tool Calls: {len(message_buffer.tool_calls)} | Mensajes: {len(message_buffer.messages)} | Reportes: {sum(1 for v in message_buffer.report_sections.values() if v)}"
    )

    layout["footer"].update(Panel(stats_table, border_style="grey50"))

def get_user_selections():
    console.print(Align.center(Panel("[bold green]TennisAgents CLI[/bold green]\n\n[dim]Multi-Agents LLM Tennis Analysis Framework[/dim]", border_style="green", padding=(1, 2))))
    console.print()

    player1, player2 = get_players()
    match_date = get_date()
    tournament = get_tournament()

    console.print(f"[green]Jugadores:[/green] {player1} vs {player2}")
    console.print(f"[green]Fecha:[/green] {match_date}")
    console.print(f"[green]Torneo:[/green] {tournament}")

    selected_analysts = select_analysts()
    console.print(f"[green]Analistas seleccionados:[/green] {', '.join(a.value for a in selected_analysts)}")

    selected_research_depth = select_research_depth()
    selected_llm_provider, backend_url = select_llm_provider()
    selected_shallow_thinker = select_shallow_thinking_agent(selected_llm_provider)
    selected_deep_thinker = select_deep_thinking_agent(selected_llm_provider)

    return {
        "player1": player1,
        "player2": player2,
        "match_date": match_date,
        "tournament": tournament,
        "analysts": selected_analysts,
        "research_depth": selected_research_depth,
        "llm_provider": selected_llm_provider.lower(),
        "backend_url": backend_url,
        "shallow_thinker": selected_shallow_thinker,
        "deep_thinker": selected_deep_thinker,
    }

def run_analysis():
    selections = get_user_selections()
    config = DEFAULT_CONFIG.copy()
    config["max_debate_rounds"] = selections["research_depth"]
    config["max_risk_discuss_rounds"] = selections["research_depth"]
    config["quick_think_llm"] = selections["shallow_thinker"]
    config["deep_think_llm"] = selections["deep_thinker"]
    config["backend_url"] = selections["backend_url"]
    config["llm_provider"] = selections["llm_provider"]

    graph = TennisAgentsGraph(
        [analyst.value for analyst in selections["analysts"]],
        config=config,
        debug=True
    )

    results_dir = Path(config.get("results_dir", "./results")) / selections["player1"] / selections["match_date"]
    results_dir.mkdir(parents=True, exist_ok=True)
    report_dir = results_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    log_file = results_dir / "message_tool.log"
    log_file.touch(exist_ok=True)

    layout = create_layout()
    with Live(layout, refresh_per_second=4) as live:
        update_display(layout)
        message_buffer.add_message("System", f"Jugadores: {selections['player1']} vs {selections['player2']}")
        message_buffer.add_message("System", f"Fecha: {selections['match_date']}")
        message_buffer.add_message("System", f"Torneo: {selections['tournament']}")
        message_buffer.add_message("System", f"Analistas: {', '.join(a.value for a in selections['analysts'])}")
        update_display(layout)

        for agent in message_buffer.agent_status:
            message_buffer.update_agent_status(agent, "pending")

        for section in message_buffer.report_sections:
            message_buffer.report_sections[section] = None
        message_buffer.current_report = None
        message_buffer.final_report = None

        first_analyst = f"{selections['analysts'][0].value.capitalize()} Analyst"
        message_buffer.update_agent_status(first_analyst, "in_progress")
        update_display(layout)

        spinner_text = f"Analizando {selections['player1']} vs {selections['player2']} ({selections['match_date']})..."
        update_display(layout, spinner_text)

        init_agent_state = graph.propagator.create_initial_state(
            selections["player1"], selections["player2"], selections["match_date"], selections["tournament"]
        )
        args = graph.propagator.get_graph_args()

        trace = []
        for chunk in graph.graph.stream(init_agent_state, **args):
            if len(chunk["messages"]) > 0:
                last_message = chunk["messages"][-1]
                content = getattr(last_message, "content", str(last_message))
                msg_type = "Reasoning" if hasattr(last_message, "content") else "System"
                message_buffer.add_message(msg_type, content)

                if hasattr(last_message, "tool_calls"):
                    for tool_call in last_message.tool_calls:
                        if isinstance(tool_call, dict):
                            message_buffer.add_tool_call(tool_call["name"], tool_call["args"])
                        else:
                            message_buffer.add_tool_call(tool_call.name, tool_call.args)

            # Actualiza reportes y estados de agentes según chunk
            for section in message_buffer.report_sections:
                if section in chunk and chunk[section] is not None:
                    message_buffer.report_sections[section] = chunk[section]

            for agent, status in chunk.get("agent_status", {}).items():
                message_buffer.update_agent_status(agent, status)

            message_buffer.current_report = chunk.get("report", None)
            update_display(layout)
            trace.append(chunk)

        # Al final del análisis
        message_buffer.final_report = trace[-1].get("report", None)
        update_display(layout, "Análisis completado.")

