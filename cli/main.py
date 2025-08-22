from typing import Optional
import datetime
import typer
from pathlib import Path
from functools import wraps
from rich.console import Console
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live
from rich.columns import Columns
from rich.markdown import Markdown
from rich.layout import Layout
from rich.text import Text
from rich.live import Live
from rich.table import Table
from collections import deque
import time
from rich.tree import Tree
from rich import box
from rich.align import Align
from rich.rule import Rule

from tennisAgents.graph.trading_graph import TennisAgentsGraph
from tennisAgents.default_config import DEFAULT_CONFIG
from cli.models import AnalystType
from cli.utils import *

console = Console()

app = typer.Typer(
    name="TennisAgents",
    help="TennisAgents CLI: Multi-Agents LLM Tennis Betting Framework",
    add_completion=True,  # Enable shell completion
)


# Create a deque to store recent messages with a maximum length
class MessageBuffer:
    def __init__(self, max_length=100):
        self.messages = deque(maxlen=max_length)
        self.tool_calls = deque(maxlen=max_length)
        self.current_report = None
        self.final_report = None  # Store the complete final report
        self.agent_status = {
            "News Analyst": "pending",
            "Odds Analyst": "pending",
            "Players Analyst": "pending",
            "Social Analyst": "pending",
            "Tournament Analyst": "pending",
            "Weather Analyst": "pending",
            "Aggressive Analyst": "pending",
            "Safe Analyst": "pending",
            "Neutral Analyst": "pending",
            "Expected Analyst": "pending",
        }
        self.current_agent = None
        self.report_sections = {
            "news_report": None,
            "odds_report": None,
            "players_report": None,
            "sentiment_report": None,
            "tournament_report": None,
            "weather_report": None,
            "risk_analysis_report": None,
            "final_bet_decision": None,
        }

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
            self._update_current_report()

    def _update_current_report(self):
        # For the panel display, only show the most recently updated section
        latest_section = None
        latest_content = None

        # Find the most recently updated section
        for section, content in self.report_sections.items():
            if content is not None:
                latest_section = section
                latest_content = content
               
        if latest_section and latest_content:
            # Format the current section for display
            section_titles = {
                "news_report": "News Analysis",
                "odds_report": "Odds Analysis",
                "players_report": "Players Analysis",
                "sentiment_report": "Social Sentiment",
                "tournament_report": "Tournament Analysis",
                "weather_report": "Weather Analysis",
                "risk_analysis_report": "Risk Analysis",
                "final_bet_decision": "Final Bet Decision",
            }
            self.current_report = (
                f"### {section_titles[latest_section]}\n{latest_content}"
            )

        # Update the final complete report
        self._update_final_report()

    def _update_final_report(self):
        report_parts = []

        # Analyst Team Reports
        if any(
            self.report_sections[section]
            for section in [
                "news_report",
                "odds_report",
                "players_report",
                "sentiment_report",
                "tournament_report",
                "weather_report",
            ]
        ):
            report_parts.append("## Analyst Team Reports")
            if self.report_sections["news_report"]:
                report_parts.append(
                    f"### News Analysis\n{self.report_sections['news_report']}"
                )
            if self.report_sections["odds_report"]:
                report_parts.append(
                    f"### Odds Analysis\n{self.report_sections['odds_report']}"
                )
            if self.report_sections["players_report"]:
                report_parts.append(
                    f"### Players Analysis\n{self.report_sections['players_report']}"
                )
            if self.report_sections["sentiment_report"]:
                report_parts.append(
                    f"### Social Sentiment\n{self.report_sections['sentiment_report']}"
                )
            if self.report_sections["tournament_report"]:
                report_parts.append(
                    f"### Tournament Analysis\n{self.report_sections['tournament_report']}"
                )
            if self.report_sections["weather_report"]:
                report_parts.append(
                    f"### Weather Analysis\n{self.report_sections['weather_report']}"
                )

        # Risk Management Team Report
        if self.report_sections["risk_analysis_report"]:
            report_parts.append("## Risk Management Analysis")
            report_parts.append(f"{self.report_sections['risk_analysis_report']}")

        # Final Bet Decision
        if self.report_sections["final_bet_decision"]:
            report_parts.append("## Final Bet Decision")
            report_parts.append(f"{self.report_sections['final_bet_decision']}")

        self.final_report = "\n\n".join(report_parts) if report_parts else None


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
    # Header with welcome message
    layout["header"].update(
        Panel(
            "[bold green]Welcome to TennisAgents CLI[/bold green]\n"
            "[dim]© [Tauric Research](https://github.com/TauricResearch)[/dim]",
            title="Welcome to TennisAgents",
            border_style="green",
            padding=(1, 2),
            expand=True,
        )
    )

    # Progress panel showing agent status
    progress_table = Table(
        show_header=True,
        header_style="bold magenta",
        show_footer=False,
        box=box.SIMPLE_HEAD,  # Use simple header with horizontal lines
        title=None,  # Remove the redundant Progress title
        padding=(0, 2),  # Add horizontal padding
        expand=True,  # Make table expand to fill available space
    )
    progress_table.add_column("Team", style="cyan", justify="center", width=20)
    progress_table.add_column("Agent", style="green", justify="center", width=20)
    progress_table.add_column("Status", style="yellow", justify="center", width=20)

    # Group agents by team
    teams = {
        "Analyst Team": [
            "News Analyst",
            "Odds Analyst",
            "Players Analyst",
            "Social Analyst",
            "Tournament Analyst",
            "Weather Analyst",
        ],
        "Risk Management": [
            "Aggressive Analyst",
            "Safe Analyst",
            "Neutral Analyst",
            "Expected Analyst",
        ],
    }

    for team, agents in teams.items():
        # Add first agent with team name
        first_agent = agents[0]
        status = message_buffer.agent_status[first_agent]
        if status == "in_progress":
            spinner = Spinner(
                "dots", text="[blue]in_progress[/blue]", style="bold cyan"
            )
            status_cell = spinner
        else:
            status_color = {
                "pending": "yellow",
                "completed": "green",
                "error": "red",
            }.get(status, "white")
            status_cell = f"[{status_color}]{status}[/{status_color}]"
        progress_table.add_row(team, first_agent, status_cell)

        # Add remaining agents in team
        for agent in agents[1:]:
            status = message_buffer.agent_status[agent]
            if status == "in_progress":
                spinner = Spinner(
                    "dots", text="[blue]in_progress[/blue]", style="bold cyan"
                )
                status_cell = spinner
            else:
                status_color = {
                    "pending": "yellow",
                    "completed": "green",
                    "error": "red",
                }.get(status, "white")
                status_cell = f"[{status_color}]{status}[/{status_color}]"
            progress_table.add_row("", agent, status_cell)

        # Add horizontal line after each team
        progress_table.add_row("─" * 20, "─" * 20, "─" * 20, style="dim")

    layout["progress"].update(
        Panel(progress_table, title="Progress", border_style="cyan", padding=(1, 2))
    )

    # Messages panel showing recent messages and tool calls
    messages_table = Table(
        show_header=True,
        header_style="bold magenta",
        show_footer=False,
        expand=True,  # Make table expand to fill available space
        box=box.MINIMAL,  # Use minimal box style for a lighter look
        show_lines=True,  # Keep horizontal lines
        padding=(0, 1),  # Add some padding between columns
    )
    messages_table.add_column("Time", style="cyan", width=8, justify="center")
    messages_table.add_column("Type", style="green", width=10, justify="center")
    messages_table.add_column(
        "Content", style="white", no_wrap=False, ratio=1
    )  # Make content column expand

    # Combine tool calls and messages
    all_messages = []

    # Add tool calls
    for timestamp, tool_name, args in message_buffer.tool_calls:
        # Truncate tool call args if too long
        if isinstance(args, str) and len(args) > 100:
            args = args[:97] + "..."
        all_messages.append((timestamp, "Tool", f"{tool_name}: {args}"))

    # Add regular messages
    for timestamp, msg_type, content in message_buffer.messages:
        # Convert content to string if it's not already
        content_str = content
        if isinstance(content, list):
            # Handle list of content blocks (Anthropic format)
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))
                    elif item.get('type') == 'tool_use':
                        text_parts.append(f"[Tool: {item.get('name', 'unknown')}]")
                else:
                    text_parts.append(str(item))
            content_str = ' '.join(text_parts)
        elif not isinstance(content_str, str):
            content_str = str(content)
            
        # Truncate message content if too long
        if len(content_str) > 200:
            content_str = content_str[:197] + "..."
        all_messages.append((timestamp, msg_type, content_str))

    # Sort by timestamp
    all_messages.sort(key=lambda x: x[0])

    # Calculate how many messages we can show based on available space
    # Start with a reasonable number and adjust based on content length
    max_messages = 12  # Increased from 8 to better fill the space

    # Get the last N messages that will fit in the panel
    recent_messages = all_messages[-max_messages:]

    # Add messages to table
    for timestamp, msg_type, content in recent_messages:
        # Format content with word wrapping
        wrapped_content = Text(content, overflow="fold")
        messages_table.add_row(timestamp, msg_type, wrapped_content)

    if spinner_text:
        messages_table.add_row("", "Spinner", spinner_text)

    # Add a footer to indicate if messages were truncated
    if len(all_messages) > max_messages:
        messages_table.footer = (
            f"[dim]Showing last {max_messages} of {len(all_messages)} messages[/dim]"
        )

    layout["messages"].update(
        Panel(
            messages_table,
            title="Messages & Tools",
            border_style="blue",
            padding=(1, 2),
        )
    )

    # Analysis panel showing current report
    if message_buffer.current_report:
        layout["analysis"].update(
            Panel(
                Markdown(message_buffer.current_report),
                title="Current Report",
                border_style="green",
                padding=(1, 2),
            )
        )
    else:
        layout["analysis"].update(
            Panel(
                "[italic]Waiting for analysis report...[/italic]",
                title="Current Report",
                border_style="green",
                padding=(1, 2),
            )
        )

    # Footer with statistics
    tool_calls_count = len(message_buffer.tool_calls)
    llm_calls_count = sum(
        1 for _, msg_type, _ in message_buffer.messages if msg_type == "Reasoning"
    )
    reports_count = sum(
        1 for content in message_buffer.report_sections.values() if content is not None
    )

    stats_table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
    stats_table.add_column("Stats", justify="center")
    stats_table.add_row(
        f"Tool Calls: {tool_calls_count} | LLM Calls: {llm_calls_count} | Generated Reports: {reports_count}"
    )

    layout["footer"].update(Panel(stats_table, border_style="grey50"))


def get_user_selections():
    """Get all user selections before starting the analysis display."""
    # Display ASCII art welcome message
    welcome_content = """
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                           TENNIS AGENTS CLI                                  ║
    ║                Multi-Agents LLM Tennis Betting Framework                     ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    """
    welcome_content += "[bold green]TennisAgents: Multi-Agents LLM Tennis Betting Framework - CLI[/bold green]\n\n"
    welcome_content += "[bold]Workflow Steps:[/bold]\n"
    welcome_content += "I. Analyst Team → II. Risk Management → III. Final Bet Decision\n\n"
    welcome_content += (
        "[dim]Built by [Tauric Research](https://github.com/TauricResearch)[/dim]"
    )

    # Create and center the welcome box
    welcome_box = Panel(
        welcome_content,
        border_style="green",
        padding=(1, 2),
        title="Welcome to TennisAgents",
        subtitle="Multi-Agents LLM Tennis Betting Framework",
    )
    console.print(Align.center(welcome_box))
    console.print()  # Add a blank line after the welcome box

    # Create a boxed questionnaire for each step
    def create_question_box(title, prompt, default=None):
        box_content = f"[bold]{title}[/bold]\n"
        box_content += f"[dim]{prompt}[/dim]"
        if default:
            box_content += f"\n[dim]Default: {default}[/dim]"
        return Panel(box_content, border_style="blue", padding=(1, 2))

    # Step 1: Player names
    console.print(
        create_question_box(
            "Step 1: Player Names", "Enter the names of the two players"
        )
    )
    player1, player2 = get_players()

    # Step 2: Tournament name
    console.print(
        create_question_box(
            "Step 2: Tournament", "Enter the tournament name"
        )
    )
    tournament = get_tournament()

    # Step 3: Analysis date
    default_date = datetime.datetime.now().strftime("%Y-%m-%d")
    console.print(
        create_question_box(
            "Step 3: Analysis Date",
            "Enter the analysis date (YYYY-MM-DD)",
            default_date,
        )
    )
    analysis_date = get_date()

    # Step 4: Wallet balance
    console.print(
        create_question_box(
            "Step 4: Wallet Balance", "Enter your wallet balance for betting"
        )
    )
    wallet_balance = get_wallet_balance()

    # Step 5: Select analysts
    console.print(
        create_question_box(
            "Step 5: Analysts Team", "Select your LLM analyst agents for the analysis"
        )
    )
    selected_analysts = select_analysts()
    console.print(
        f"[green]Selected analysts:[/green] {', '.join(analyst.value for analyst in selected_analysts)}"
    )

    # Step 6: Research depth
    console.print(
        create_question_box(
            "Step 6: Research Depth", "Select your research depth level"
        )
    )
    selected_research_depth = select_research_depth()

    # Step 7: OpenAI backend
    console.print(
        create_question_box(
            "Step 7: OpenAI backend", "Select which service to talk to"
        )
    )
    selected_llm_provider, backend_url = select_llm_provider()
    
    # Step 8: Thinking agents
    console.print(
        create_question_box(
            "Step 8: Thinking Agents", "Select your thinking agents for analysis"
        )
    )
    selected_shallow_thinker = select_shallow_thinking_agent(selected_llm_provider)
    selected_deep_thinker = select_deep_thinking_agent(selected_llm_provider)

    return {
        "player1": player1,
        "player2": player2,
        "tournament": tournament,
        "analysis_date": analysis_date,
        "wallet_balance": wallet_balance,
        "analysts": selected_analysts,
        "research_depth": selected_research_depth,
        "llm_provider": selected_llm_provider.lower(),
        "backend_url": backend_url,
        "shallow_thinker": selected_shallow_thinker,
        "deep_thinker": selected_deep_thinker,
    }


def display_complete_report(final_state):
    """Display the complete analysis report with team-based panels."""
    console.print("\n[bold green]Complete Analysis Report[/bold green]\n")

    # I. Analyst Team Reports
    analyst_reports = []

    # News Analyst Report
    if final_state.get("news_report"):
        analyst_reports.append(
            Panel(
                Markdown(final_state["news_report"]),
                title="News Analyst",
                border_style="blue",
                padding=(1, 2),
            )
        )

    # Odds Analyst Report
    if final_state.get("odds_report"):
        analyst_reports.append(
            Panel(
                Markdown(final_state["odds_report"]),
                title="Odds Analyst",
                border_style="blue",
                padding=(1, 2),
            )
        )

    # Players Analyst Report
    if final_state.get("players_report"):
        analyst_reports.append(
            Panel(
                Markdown(final_state["players_report"]),
                title="Players Analyst",
                border_style="blue",
                padding=(1, 2),
            )
        )

    # Social Analyst Report
    if final_state.get("sentiment_report"):
        analyst_reports.append(
            Panel(
                Markdown(final_state["sentiment_report"]),
                title="Social Analyst",
                border_style="blue",
                padding=(1, 2),
            )
        )

    # Tournament Analyst Report
    if final_state.get("tournament_report"):
        analyst_reports.append(
            Panel(
                Markdown(final_state["tournament_report"]),
                title="Tournament Analyst",
                border_style="blue",
                padding=(1, 2),
            )
        )

    # Weather Analyst Report
    if final_state.get("weather_report"):
        analyst_reports.append(
            Panel(
                Markdown(final_state["weather_report"]),
                title="Weather Analyst",
                border_style="blue",
                padding=(1, 2),
            )
        )

    if analyst_reports:
        console.print(
            Panel(
                Columns(analyst_reports, equal=True, expand=True),
                title="I. Analyst Team Reports",
                border_style="cyan",
                padding=(1, 2),
            )
        )

    # II. Risk Management Team Reports
    if final_state.get("risk_debate_state"):
        risk_reports = []
        risk_state = final_state["risk_debate_state"]

        # Aggressive Analyst Analysis
        if risk_state.get("aggressive_history"):
            risk_reports.append(
                Panel(
                    Markdown(risk_state["aggressive_history"]),
                    title="Aggressive Analyst",
                    border_style="blue",
                    padding=(1, 2),
                )
            )

        # Safe Analyst Analysis
        if risk_state.get("safe_history"):
            risk_reports.append(
                Panel(
                    Markdown(risk_state["safe_history"]),
                    title="Safe Analyst",
                    border_style="blue",
                    padding=(1, 2),
                )
            )

        # Neutral Analyst Analysis
        if risk_state.get("neutral_history"):
            risk_reports.append(
                Panel(
                    Markdown(risk_state["neutral_history"]),
                    title="Neutral Analyst",
                    border_style="blue",
                    padding=(1, 2),
                )
            )

        # Expected Analyst Analysis
        if risk_state.get("expected_history"):
            risk_reports.append(
                Panel(
                    Markdown(risk_state["expected_history"]),
                    title="Expected Analyst",
                    border_style="blue",
                    padding=(1, 2),
                )
            )

        if risk_reports:
            console.print(
                Panel(
                    Columns(risk_reports, equal=True, expand=True),
                    title="II. Risk Management Team Analysis",
                    border_style="red",
                    padding=(1, 2),
                )
            )

    # III. Final Bet Decision
    if final_state.get("final_bet_decision"):
        console.print(
            Panel(
                Panel(
                    Markdown(final_state["final_bet_decision"]),
                    title="Final Bet Decision",
                    border_style="blue",
                    padding=(1, 2),
                ),
                title="III. Final Bet Decision",
                border_style="green",
                padding=(1, 2),
            )
        )




def extract_content_string(content):
    """Extract string content from various message formats."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        # Handle Anthropic's list format
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get('type') == 'text':
                    text_parts.append(item.get('text', ''))
                elif item.get('type') == 'tool_use':
                    text_parts.append(f"[Tool: {item.get('name', 'unknown')}]")
            else:
                text_parts.append(str(item))
        return ' '.join(text_parts)
    else:
        return str(content)

def run_analysis():
    # First get all user selections
    selections = get_user_selections()

    # Create config with selected research depth
    config = DEFAULT_CONFIG.copy()
    config["max_debate_rounds"] = selections["research_depth"]
    config["max_risk_discuss_rounds"] = selections["research_depth"]
    config["quick_think_llm"] = selections["shallow_thinker"]
    config["deep_think_llm"] = selections["deep_thinker"]
    config["backend_url"] = selections["backend_url"]
    config["llm_provider"] = selections["llm_provider"].lower()

    # Initialize the graph
    graph = TennisAgentsGraph(
        [analyst.value for analyst in selections["analysts"]], config=config, debug=True
    )

    # Create result directory
    player_pair = f"{selections['player1']} vs {selections['player2']}"
    results_dir = Path(config["results_dir"]) / player_pair / selections["analysis_date"]
    results_dir.mkdir(parents=True, exist_ok=True)
    report_dir = results_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    log_file = results_dir / "message_tool.log"
    log_file.touch(exist_ok=True)

    def save_message_decorator(obj, func_name):
        func = getattr(obj, func_name)
        @wraps(func)
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            timestamp, message_type, content = obj.messages[-1]
            content = content.replace("\n", " ")  # Replace newlines with spaces
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} [{message_type}] {content}\n")
        return wrapper
    
    def save_tool_call_decorator(obj, func_name):
        func = getattr(obj, func_name)
        @wraps(func)
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            timestamp, tool_name, args = obj.tool_calls[-1]
            args_str = ", ".join(f"{k}={v}" for k, v in args.items())
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} [Tool Call] {tool_name}({args_str})\n")
        return wrapper

    def save_report_section_decorator(obj, func_name):
        func = getattr(obj, func_name)
        @wraps(func)
        def wrapper(section_name, content):
            func(section_name, content)
            if section_name in obj.report_sections and obj.report_sections[section_name] is not None:
                content = obj.report_sections[section_name]
                if content:
                    file_name = f"{section_name}.md"
                    with open(report_dir / file_name, "w", encoding="utf-8") as f:
                        f.write(content)
        return wrapper

    message_buffer.add_message = save_message_decorator(message_buffer, "add_message")
    message_buffer.add_tool_call = save_tool_call_decorator(message_buffer, "add_tool_call")
    message_buffer.update_report_section = save_report_section_decorator(message_buffer, "update_report_section")

    # Now start the display layout
    layout = create_layout()

    with Live(layout, refresh_per_second=4) as live:
        # Initial display
        update_display(layout)

        # Add initial messages
        message_buffer.add_message("System", f"Player 1: {selections['player1']}")
        message_buffer.add_message("System", f"Player 2: {selections['player2']}")
        message_buffer.add_message("System", f"Tournament: {selections['tournament']}")
        message_buffer.add_message(
            "System", f"Analysis date: {selections['analysis_date']}"
        )
        message_buffer.add_message(
            "System", f"Wallet balance: €{selections['wallet_balance']:.2f}"
        )
        message_buffer.add_message(
            "System",
            f"Selected analysts: {', '.join(analyst.value for analyst in selections['analysts'])}",
        )
        update_display(layout)

        # Reset agent statuses
        for agent in message_buffer.agent_status:
            message_buffer.update_agent_status(agent, "pending")

        # Reset report sections
        for section in message_buffer.report_sections:
            message_buffer.report_sections[section] = None
        message_buffer.current_report = None
        message_buffer.final_report = None

        # Update agent status to in_progress for the first analyst
        first_analyst = f"{selections['analysts'][0].value.capitalize()} Analyst"
        message_buffer.update_agent_status(first_analyst, "in_progress")
        update_display(layout)

        # Create spinner text
        player_pair = f"{selections['player1']} vs {selections['player2']}"
        spinner_text = (
            f"Analyzing {player_pair} on {selections['analysis_date']}..."
        )
        update_display(layout, spinner_text)

        # Initialize state and get graph args
        init_agent_state = graph.propagator.create_initial_state(
            selections["player1"], 
            selections["player2"], 
            selections["analysis_date"],
            selections["tournament"],
            selections["wallet_balance"]
        )
        args = graph.propagator.get_graph_args()
        
        # Debug: Print initial state keys
        console.print(f"[yellow]Debug: Initial state keys: {list(init_agent_state.keys())}[/yellow]")

        # Stream the analysis
        trace = []
        for chunk in graph.graph.stream(init_agent_state, **args):
            if len(chunk["messages"]) > 0:
                # Get the last message from the chunk
                last_message = chunk["messages"][-1]

                # Extract message content and type
                if hasattr(last_message, "content"):
                    content = extract_content_string(last_message.content)  # Use the helper function
                    msg_type = "Reasoning"
                else:
                    content = str(last_message)
                    msg_type = "System"

                # Add message to buffer
                message_buffer.add_message(msg_type, content)                

                # If it's a tool call, add it to tool calls
                if hasattr(last_message, "tool_calls"):
                    for tool_call in last_message.tool_calls:
                        # Handle both dictionary and object tool calls
                        if isinstance(tool_call, dict):
                            message_buffer.add_tool_call(
                                tool_call["name"], tool_call["args"]
                            )
                        else:
                            message_buffer.add_tool_call(tool_call.name, tool_call.args)

                # Update reports and agent status based on chunk content
                # Analyst Team Reports
                if "news_report" in chunk and chunk["news_report"]:
                    message_buffer.update_report_section(
                        "news_report", chunk["news_report"]
                    )
                    message_buffer.update_agent_status("News Analyst", "completed")
                    # Set next analyst to in_progress
                    if "odds" in selections["analysts"]:
                        message_buffer.update_agent_status(
                            "Odds Analyst", "in_progress"
                        )

                if "odds_report" in chunk and chunk["odds_report"]:
                    message_buffer.update_report_section(
                        "odds_report", chunk["odds_report"]
                    )
                    message_buffer.update_agent_status("Odds Analyst", "completed")
                    # Set next analyst to in_progress
                    if "players" in selections["analysts"]:
                        message_buffer.update_agent_status(
                            "Players Analyst", "in_progress"
                        )

                if "players_report" in chunk and chunk["players_report"]:
                    message_buffer.update_report_section(
                        "players_report", chunk["players_report"]
                    )
                    message_buffer.update_agent_status("Players Analyst", "completed")
                    # Set next analyst to in_progress
                    if "social" in selections["analysts"]:
                        message_buffer.update_agent_status(
                            "Social Analyst", "in_progress"
                        )

                if "sentiment_report" in chunk and chunk["sentiment_report"]:
                    message_buffer.update_report_section(
                        "sentiment_report", chunk["sentiment_report"]
                    )
                    message_buffer.update_agent_status("Social Analyst", "completed")
                    # Set next analyst to in_progress
                    if "tournament" in selections["analysts"]:
                        message_buffer.update_agent_status(
                            "Tournament Analyst", "in_progress"
                        )

                if "tournament_report" in chunk and chunk["tournament_report"]:
                    message_buffer.update_report_section(
                        "tournament_report", chunk["tournament_report"]
                    )
                    message_buffer.update_agent_status("Tournament Analyst", "completed")
                    # Set next analyst to in_progress
                    if "weather" in selections["analysts"]:
                        message_buffer.update_agent_status(
                            "Weather Analyst", "in_progress"
                        )

                if "weather_report" in chunk and chunk["weather_report"]:
                    message_buffer.update_report_section(
                        "weather_report", chunk["weather_report"]
                    )
                    message_buffer.update_agent_status("Weather Analyst", "completed")
                    # Set first risk management analyst to in_progress
                    message_buffer.update_agent_status("Aggressive Analyst", "in_progress")

                # Risk Management Team - Handle Risk Debate State
                if "risk_debate_state" in chunk and chunk["risk_debate_state"]:
                    risk_state = chunk["risk_debate_state"]

                    # Update Aggressive Analyst status and report
                    if "aggressive_history" in risk_state and risk_state["aggressive_history"]:
                        message_buffer.update_agent_status("Aggressive Analyst", "in_progress")
                        # Extract latest aggressive response
                        aggressive_responses = risk_state["aggressive_history"].split("\n")
                        latest_aggressive = aggressive_responses[-1] if aggressive_responses else ""
                        if latest_aggressive:
                            message_buffer.add_message("Reasoning", f"Aggressive Analyst: {latest_aggressive}")

                    # Update Safe Analyst status and report
                    if "safe_history" in risk_state and risk_state["safe_history"]:
                        message_buffer.update_agent_status("Safe Analyst", "in_progress")
                        # Extract latest safe response
                        safe_responses = risk_state["safe_history"].split("\n")
                        latest_safe = safe_responses[-1] if safe_responses else ""
                        if latest_safe:
                            message_buffer.add_message("Reasoning", f"Safe Analyst: {latest_safe}")

                    # Update Neutral Analyst status and report
                    if "neutral_history" in risk_state and risk_state["neutral_history"]:
                        message_buffer.update_agent_status("Neutral Analyst", "in_progress")
                        # Extract latest neutral response
                        neutral_responses = risk_state["neutral_history"].split("\n")
                        latest_neutral = neutral_responses[-1] if neutral_responses else ""
                        if latest_neutral:
                            message_buffer.add_message("Reasoning", f"Neutral Analyst: {latest_neutral}")

                    # Update Expected Analyst status and report
                    if "expected_history" in risk_state and risk_state["expected_history"]:
                        message_buffer.update_agent_status("Expected Analyst", "in_progress")
                        # Extract latest expected response
                        expected_responses = risk_state["expected_history"].split("\n")
                        latest_expected = expected_responses[-1] if expected_responses else ""
                        if latest_expected:
                            message_buffer.add_message("Reasoning", f"Expected Analyst: {latest_expected}")

                    # Update risk analysis report with all analysts' input
                    risk_report_parts = []
                    if risk_state.get("aggressive_history"):
                        risk_report_parts.append(f"### Aggressive Analyst Analysis\n{risk_state['aggressive_history']}")
                    if risk_state.get("safe_history"):
                        risk_report_parts.append(f"### Safe Analyst Analysis\n{risk_state['safe_history']}")
                    if risk_state.get("neutral_history"):
                        risk_report_parts.append(f"### Neutral Analyst Analysis\n{risk_state['neutral_history']}")
                    if risk_state.get("expected_history"):
                        risk_report_parts.append(f"### Expected Analyst Analysis\n{risk_state['expected_history']}")
                    
                    if risk_report_parts:
                        message_buffer.update_report_section("risk_analysis_report", "\n\n".join(risk_report_parts))

                    # If all risk analysts have provided input, mark them as completed
                    if all(key in risk_state for key in ["aggressive_history", "safe_history", "neutral_history", "expected_history"]):
                        message_buffer.update_agent_status("Aggressive Analyst", "completed")
                        message_buffer.update_agent_status("Safe Analyst", "completed")
                        message_buffer.update_agent_status("Neutral Analyst", "completed")
                        message_buffer.update_agent_status("Expected Analyst", "completed")

                # Final Bet Decision
                if "final_bet_decision" in chunk and chunk["final_bet_decision"]:
                    message_buffer.update_report_section(
                        "final_bet_decision", chunk["final_bet_decision"]
                    )

                # Update the display
                update_display(layout)

            trace.append(chunk)
        # Get final state and decision
        final_state = trace[-1]
        decision = graph.process_signal(final_state["final_bet_decision"])

        # Update all agent statuses to completed
        for agent in message_buffer.agent_status:
            message_buffer.update_agent_status(agent, "completed")

        message_buffer.add_message(
            "Analysis", f"Completed analysis for {selections['analysis_date']}"
        )

        # Update final report sections
        for section in message_buffer.report_sections.keys():
            if section in final_state:
                message_buffer.update_report_section(section, final_state[section])

        # Display the complete final report
        display_complete_report(final_state)

        update_display(layout)


@app.command()
def analyze():
    run_analysis()


if __name__ == "__main__":
    app()
