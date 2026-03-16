"""
FastAPI server for TennisAgents web application
"""
import sys
from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import requests
from datetime import datetime
import re

# Add parent directory to path to import tennisAgents modules
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import Sportradar utilities
from tennisAgents.dataflows.match_live_utils import fetch_live_summaries, fetch_season_summaries, fetch_daily_summaries, get_sportradar_api_key
from tennisAgents.default_config import DEFAULT_CONFIG
from tennisAgents.graph.trading_graph import TennisAgentsGraph
from tennisAgents.utils.earnings_manager import EarningsManager

from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json

# Create FastAPI app
app = FastAPI(
    title="TennisAgents",
    description="Multi-Agents LLM Tennis Betting Framework",
    version="1.0.0"
)

# Setup paths
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
IMG_DIR = BASE_DIR / "img"
DATA_DIR = PROJECT_ROOT / "web" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
WEB_RESULTS_DIR = PROJECT_ROOT / "web" / "results"
CLI_RESULTS_DIR = PROJECT_ROOT / "results"

# Helper function to extract content string (copied from cli/main.py)
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

class AnalysisRequest(BaseModel):
    player1: str
    player2: str
    tournament: str
    analysis_date: str
    wallet_balance: float
    analysts: List[str]
    research_depth: int
    llm_provider: str
    shallow_thinker: str
    deep_thinker: str
    backend_url: Optional[str] = None

@app.post("/api/run-analysis")
async def run_analysis(request: Request, analysis_request: AnalysisRequest):
    """
    Run the tennis analysis system and stream the results.
    """
    
    async def event_generator():
        results_dir = None
        try:
            # Setup configuration
            config = DEFAULT_CONFIG.copy()
            config["max_debate_rounds"] = analysis_request.research_depth
            config["max_risk_discuss_rounds"] = analysis_request.research_depth
            config["quick_think_llm"] = analysis_request.shallow_thinker
            config["deep_think_llm"] = analysis_request.deep_thinker
            if analysis_request.backend_url:
                config["backend_url"] = analysis_request.backend_url
            config["llm_provider"] = analysis_request.llm_provider.lower()
            
            # For web runs, force results into web/results (separado de la CLI)
            web_results_root = PROJECT_ROOT / "web" / "results"
            web_results_root.mkdir(parents=True, exist_ok=True)
            config["results_dir"] = str(web_results_root)
                
            # Setup results directory
            player_pair = f"{analysis_request.player1} vs {analysis_request.player2}"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_dir_name = f"{player_pair}_{timestamp}"
            results_dir = Path(config["results_dir"]) / unique_dir_name / analysis_request.analysis_date
            results_dir.mkdir(parents=True, exist_ok=True)
            report_dir = results_dir / "reports"
            report_dir.mkdir(parents=True, exist_ok=True)
            log_file = results_dir / "message_tool.log"
            log_file.touch(exist_ok=True)
            
            # Initial status: In Progress
            status_file = results_dir / "status.json"
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump({
                    "status": "in_progress",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "player1": analysis_request.player1,
                    "player2": analysis_request.player2,
                    "tournament": analysis_request.tournament
                }, f)
            
            # Determinar el nombre del modelo para etiquetar informes de analistas
            # Analistas locales (News, Social, Tournament, Weather) pueden usar un LLM distinto
            if config.get("use_local_analysts", False):
                analyst_model_name = config.get(
                    "local_model_name",
                    config.get("deep_think_llm", "unknown_model"),
                )
            else:
                analyst_model_name = config.get("deep_think_llm", "unknown_model")

            # Modelo principal usado por el resto de analistas (Players, Match Live, etc.)
            main_model_name = config.get("deep_think_llm", "unknown_model")

            def _sanitize_model_name(name: str) -> str:
                return str(name).replace("/", "_").replace("\\", "_").replace(":", "_")

            safe_analyst_model_name = _sanitize_model_name(analyst_model_name)
            safe_main_model_name = _sanitize_model_name(main_model_name)
            
            # Initialize graph
            # Note: TennisAgentsGraph is synchronous, but we run it in a way that we can stream
            # Since graph initialization might take a moment, send a status update
            yield json.dumps({
                "type": "status", 
                "data": {"message": "Initializing analysis graph...", "step": "init"}
            }) + "\n"
            
            graph = TennisAgentsGraph(
                analysis_request.analysts, 
                config=config, 
                debug=True
            )
            
            # Helper interno para escribir en el log de mensajes/herramientas
            def append_log_line(line: str) -> None:
                try:
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                except Exception:
                    # No romper el streaming por un fallo de escritura
                    pass
            
            # Initialize state
            init_agent_state = graph.propagator.create_initial_state(
                analysis_request.player1, 
                analysis_request.player2, 
                analysis_request.analysis_date,
                analysis_request.tournament,
                analysis_request.wallet_balance
            )
            args = graph.propagator.get_graph_args()
            
            yield json.dumps({
                "type": "status", 
                "data": {"message": f"Starting analysis for {player_pair}...", "step": "started"}
            }) + "\n"

            # Stream the analysis
            # Since graph.stream is a generator, we iterate over it
            for chunk in graph.graph.stream(init_agent_state, **args):
                
                # Check for client disconnection (cancellation)
                if await request.is_disconnected():
                    print(f"Client disconnected during analysis of {player_pair}")
                    # Mark as cancelled
                    if results_dir:
                        status_file = results_dir / "status.json"
                        with open(status_file, "w", encoding="utf-8") as f:
                            json.dump({
                                "status": "cancelled",
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "player1": analysis_request.player1,
                                "player2": analysis_request.player2,
                                "tournament": analysis_request.tournament
                            }, f)
                    return # Stop generator

                # 1. Handle Messages (Logs)
                if "messages" in chunk and len(chunk["messages"]) > 0:
                    last_message = chunk["messages"][-1]
                    
                    msg_content = ""
                    msg_type = "System"
                    
                    if hasattr(last_message, "content"):
                        msg_content = extract_content_string(last_message.content)
                        msg_type = "Reasoning"
                    else:
                        msg_content = str(last_message)
                    
                    log_event = {
                        "type": "log",
                        "data": {
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "type": msg_type,
                            "content": msg_content
                        }
                    }
                    # Escribir en fichero de log
                    append_log_line(f"{log_event['data']['timestamp']} [{log_event['data']['type']}] {log_event['data']['content'].replace(chr(10), ' ')}")
                    # Enviar al frontend
                    yield json.dumps(log_event) + "\n"
                    
                    # Handle tool calls
                    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                        for tool_call in last_message.tool_calls:
                            tool_name = tool_call["name"] if isinstance(tool_call, dict) else tool_call.name
                            tool_args = tool_call["args"] if isinstance(tool_call, dict) else tool_call.args
                            
                            tool_event = {
                                "type": "tool_call",
                                "data": {
                                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                                    "name": tool_name,
                                    "args": str(tool_args)
                                }
                            }
                            # Log de tool call
                            append_log_line(f"{tool_event['data']['timestamp']} [Tool Call] {tool_event['data']['name']}({tool_event['data']['args']})")
                            # Enviar al frontend
                            yield json.dumps(tool_event) + "\n"

                # 2. Handle Reports and Agent Status Updates
                
                # News Analyst
                if "news_report" in chunk and chunk["news_report"]:
                    content = chunk["news_report"]
                    # Guardar en fichero Markdown usando el modelo del analista
                    file_name = f"news_report_{safe_analyst_model_name}.md"
                    try:
                        with open(report_dir / file_name, "w", encoding="utf-8") as f:
                            f.write(content)
                    except Exception:
                        pass
                    yield json.dumps({
                        "type": "report",
                        "data": {"section": "news_report", "content": content}
                    }) + "\n"
                    yield json.dumps({
                        "type": "agent_status",
                        "data": {"agent": "News Analyst", "status": "completed"}
                    }) + "\n"

                # Odds Analyst
                if "odds_report" in chunk and chunk["odds_report"]:
                    content = chunk["odds_report"]
                    try:
                        # Odds Analyst no usa LLM, mantenemos nombre fijo
                        with open(report_dir / "odds_report.md", "w", encoding="utf-8") as f:
                            f.write(content)
                    except Exception:
                        pass
                    yield json.dumps({
                        "type": "report",
                        "data": {"section": "odds_report", "content": content}
                    }) + "\n"
                    yield json.dumps({
                        "type": "agent_status",
                        "data": {"agent": "Odds Analyst", "status": "completed"}
                    }) + "\n"

                # Players Analyst
                if "players_report" in chunk and chunk["players_report"]:
                    content = chunk["players_report"]
                    try:
                        file_name = f"players_report_{safe_main_model_name}.md"
                        with open(report_dir / file_name, "w", encoding="utf-8") as f:
                            f.write(content)
                    except Exception:
                        pass
                    yield json.dumps({
                        "type": "report",
                        "data": {"section": "players_report", "content": content}
                    }) + "\n"
                    yield json.dumps({
                        "type": "agent_status",
                        "data": {"agent": "Players Analyst", "status": "completed"}
                    }) + "\n"

                # Social Analyst
                if "sentiment_report" in chunk and chunk["sentiment_report"]:
                    content = chunk["sentiment_report"]
                    try:
                        file_name = f"sentiment_report_{safe_analyst_model_name}.md"
                        with open(report_dir / file_name, "w", encoding="utf-8") as f:
                            f.write(content)
                    except Exception:
                        pass
                    yield json.dumps({
                        "type": "report",
                        "data": {"section": "sentiment_report", "content": content}
                    }) + "\n"
                    yield json.dumps({
                        "type": "agent_status",
                        "data": {"agent": "Social Analyst", "status": "completed"}
                    }) + "\n"

                # Tournament Analyst
                if "tournament_report" in chunk and chunk["tournament_report"]:
                    content = chunk["tournament_report"]
                    try:
                        file_name = f"tournament_report_{safe_analyst_model_name}.md"
                        with open(report_dir / file_name, "w", encoding="utf-8") as f:
                            f.write(content)
                    except Exception:
                        pass
                    yield json.dumps({
                        "type": "report",
                        "data": {"section": "tournament_report", "content": content}
                    }) + "\n"
                    yield json.dumps({
                        "type": "agent_status",
                        "data": {"agent": "Tournament Analyst", "status": "completed"}
                    }) + "\n"

                # Weather Analyst
                if "weather_report" in chunk and chunk["weather_report"]:
                    content = chunk["weather_report"]
                    try:
                        file_name = f"weather_report_{safe_analyst_model_name}.md"
                        with open(report_dir / file_name, "w", encoding="utf-8") as f:
                            f.write(content)
                    except Exception:
                        pass
                    yield json.dumps({
                        "type": "report",
                        "data": {"section": "weather_report", "content": content}
                    }) + "\n"
                    yield json.dumps({
                        "type": "agent_status",
                        "data": {"agent": "Weather Analyst", "status": "completed"}
                    }) + "\n"

                # Match Live Analyst
                if "match_live_report" in chunk and chunk["match_live_report"]:
                    content = chunk["match_live_report"]
                    try:
                        file_name = f"match_live_report_{safe_main_model_name}.md"
                        with open(report_dir / file_name, "w", encoding="utf-8") as f:
                            f.write(content)
                    except Exception:
                        pass
                    yield json.dumps({
                        "type": "report",
                        "data": {"section": "match_live_report", "content": content}
                    }) + "\n"
                    yield json.dumps({
                        "type": "agent_status",
                        "data": {"agent": "Match Live Analyst", "status": "completed"}
                    }) + "\n"

                # Risk Management Debate
                if "risk_debate_state" in chunk and chunk["risk_debate_state"]:
                    risk_state = chunk["risk_debate_state"]
                    
                    # Stream specific analyst inputs if available
                    if "aggressive_history" in risk_state:
                        yield json.dumps({
                            "type": "risk_update",
                            "data": {"analyst": "Aggressive Analyst", "content": risk_state["aggressive_history"]}
                        }) + "\n"
                    if "safe_history" in risk_state:
                        yield json.dumps({
                            "type": "risk_update",
                            "data": {"analyst": "Safe Analyst", "content": risk_state["safe_history"]}
                        }) + "\n"
                    if "neutral_history" in risk_state:
                        yield json.dumps({
                            "type": "risk_update",
                            "data": {"analyst": "Neutral Analyst", "content": risk_state["neutral_history"]}
                        }) + "\n"
                    if "expected_history" in risk_state:
                        yield json.dumps({
                            "type": "risk_update",
                            "data": {"analyst": "Expected Analyst", "content": risk_state["expected_history"]}
                        }) + "\n"

                # Final Decision
                if "final_bet_decision" in chunk and chunk["final_bet_decision"]:
                    content = chunk["final_bet_decision"]
                    # Guardar decisión final principal
                    try:
                        with open(report_dir / "final_bet_decision.md", "w", encoding="utf-8") as f:
                            f.write(content)
                    except Exception:
                        pass
                    yield json.dumps({
                        "type": "report",
                        "data": {"section": "final_bet_decision", "content": content}
                    }) + "\n"
                    
                # Individual Risk Manager Decisions
                if "individual_risk_manager_decisions" in chunk and chunk["individual_risk_manager_decisions"]:
                    individual_decisions = chunk["individual_risk_manager_decisions"]
                    # Guardar cada decisión individual en su propio fichero (como en la CLI)
                    if isinstance(individual_decisions, dict):
                        for model_name, decision in individual_decisions.items():
                            safe_model_name = model_name.replace("/", "_").replace("\\", "_").replace(":", "_")
                            file_name = f"final_bet_decision_{safe_model_name}.md"
                            try:
                                with open(report_dir / file_name, "w", encoding="utf-8") as f:
                                    f.write(f"# Final Bet Decision - {model_name}\n\n{decision}")
                            except Exception:
                                pass
                    yield json.dumps({
                        "type": "individual_decisions",
                        "data": individual_decisions
                    }) + "\n"

                # Final Synthesis Report
                if "final_response" in chunk and chunk["final_response"]:
                    content = chunk["final_response"]
                    try:
                        with open(report_dir / "final_response.md", "w", encoding="utf-8") as f:
                            f.write(content)
                    except Exception:
                        pass
                    yield json.dumps({
                        "type": "report",
                        "data": {"section": "final_response", "content": content}
                    }) + "\n"

            # Mark as completed
            if results_dir:
                status_file = results_dir / "status.json"
                with open(status_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "status": "completed",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "player1": analysis_request.player1,
                        "player2": analysis_request.player2,
                        "tournament": analysis_request.tournament
                    }, f)

            yield json.dumps({
                "type": "status",
                "data": {
                    "message": "Analysis complete!",
                    "step": "completed",
                    "match_dir": unique_dir_name,
                    "analysis_date": analysis_request.analysis_date,
                    "storage": "web"
                }
            }) + "\n"

        except Exception as e:
            # Check if it was a cancellation (sometimes manifests as exception)
            if "disconnect" in str(e).lower() or "cancel" in str(e).lower():
                 if results_dir:
                    status_file = results_dir / "status.json"
                    with open(status_file, "w", encoding="utf-8") as f:
                        json.dump({
                            "status": "cancelled",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "player1": analysis_request.player1,
                            "player2": analysis_request.player2,
                            "tournament": analysis_request.tournament
                        }, f)
            else:
                # Mark as error
                if results_dir:
                    status_file = results_dir / "status.json"
                    with open(status_file, "w", encoding="utf-8") as f:
                        json.dump({
                            "status": "error",
                            "error": str(e),
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "player1": analysis_request.player1,
                            "player2": analysis_request.player2,
                            "tournament": analysis_request.tournament
                        }, f)

            yield json.dumps({
                "type": "error",
                "data": {"message": str(e)}
            }) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/img", StaticFiles(directory=str(IMG_DIR)), name="img")

# Setup templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    """Register page"""
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/predict", response_class=HTMLResponse)
async def predict(request: Request):
    """Predict page"""
    return templates.TemplateResponse("predict.html", {"request": request})


@app.get("/daily-summaries", response_class=HTMLResponse)
async def daily_summaries(request: Request):
    """Daily summaries page"""
    return templates.TemplateResponse("daily-summaries.html", {"request": request})


@app.get("/predicted", response_class=HTMLResponse)
async def predicted(request: Request):
    """Predicted matches page"""
    return templates.TemplateResponse("predicted.html", {"request": request})


@app.get("/ganancias", response_class=HTMLResponse)
async def ganancias(request: Request):
    """Earnings / profit history page"""
    return templates.TemplateResponse("ganancias.html", {"request": request})


def fetch_competitor_profile(competitor_id: str) -> Dict[str, Any]:
    """
    Obtiene el perfil de un competidor desde la API de Sportradar.
    
    Args:
        competitor_id (str): ID del competidor (puede estar vacío)
    
    Returns:
        Dict[str, Any]: Diccionario con:
            - success (bool): Si la operación fue exitosa
            - data (Dict): Datos del perfil del competidor
            - competitor_id (str): ID del competidor
            - fetched_at (str): Timestamp de la consulta
            - error (str): Mensaje de error si falló
    """
    try:
        if not competitor_id:
            return {
                "success": False,
                "error": "competitor_id está vacío",
                "competitor_id": "",
                "data": {},
                "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        api_key = get_sportradar_api_key()
        access_level = DEFAULT_CONFIG.get("sportradar_access_level", "trial")
        language = DEFAULT_CONFIG.get("sportradar_language", "en")
        
        url = f"https://api.sportradar.com/tennis/{access_level}/v3/{language}/competitors/{competitor_id}/profile.json"
        headers = {
            "accept": "application/json",
            "x-api-key": api_key
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        return {
            "success": True,
            "data": data,
            "competitor_id": competitor_id,
            "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except requests.exceptions.HTTPError as http_err:
        return {
            "success": False,
            "error": f"Error HTTP: {str(http_err)}",
            "competitor_id": competitor_id,
            "data": {},
            "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "status_code": response.status_code if 'response' in locals() else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error: {str(e)}",
            "competitor_id": competitor_id,
            "data": {},
            "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


@app.post("/api/fetch-live-matches")
async def fetch_live_matches():
    """
    Endpoint para obtener partidos en vivo de Sportradar y guardarlos.
    También obtiene los perfiles de los dos jugadores (aunque los IDs estén vacíos).
    Ahora también llama al endpoint de season summaries.
    """
    try:
        # Llamar a la función que obtiene los partidos en vivo
        # Solo incluir partidos con estado "live" (en directo)
        result = fetch_live_summaries(include_all_statuses=False)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Error desconocido al obtener partidos")
            )
        
        # Guardar los datos en un archivo JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"live_matches_{timestamp}.json"
        filepath = DATA_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result["data"], f, indent=2, ensure_ascii=False)
        
        # Intentar obtener un season_id real de los partidos obtenidos
        season_id = "test_season_id"  # Default fallback
        
        # Buscar el primer season_id válido en los summaries
        if result.get("success") and result.get("data") and result["data"].get("summaries"):
            for summary in result["data"]["summaries"]:
                try:
                    current_season_id = summary.get("sport_event", {}).get("sport_event_context", {}).get("season", {}).get("id")
                    if current_season_id:
                        season_id = current_season_id
                        break
                except Exception:
                    continue
        
        # Si seguimos con el placeholder y no queremos causar error 429/404 innecesario,
        # podríamos omitir la llamada, pero mantenemos la estructura solicitada intentando evitar el error si es posible.
        
        access_level = DEFAULT_CONFIG.get("sportradar_access_level", "trial")
        language_code = DEFAULT_CONFIG.get("sportradar_language", "en")
        
        # Solo llamar si tenemos un season_id que parece real (empieza por sr:season) o si queremos mantener el comportamiento de test
        if season_id.startswith("sr:season:") or season_id == "test_season_id":
             # Si es el test_id, tal vez queramos evitar el 429 spameando. 
             # Pero el log mostraba que se llamaba explícitamente.
             pass

        season_result = fetch_season_summaries(
            season_id=season_id,
            access_level=access_level,
            language_code=language_code,
            format="json"
        )
        
        # Guardar los datos de season summaries también (aunque den error)
        season_filename = f"season_summaries_{timestamp}.json"
        season_filepath = DATA_DIR / season_filename
        
        season_data_to_save = {
            "season_id": season_id,
            "result": season_result,
            "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(season_filepath, "w", encoding="utf-8") as f:
            json.dump(season_data_to_save, f, indent=2, ensure_ascii=False)
        
        # Construir mensaje de respuesta incluyendo información del season summaries
        message = f"Se obtuvieron {result['total_matches']} partidos"
        if season_result.get("success"):
            message += f". Season summaries obtenidos exitosamente para season_id: {season_id}"
        else:
            message += f". Season summaries falló (esperado): {season_result.get('error', 'Error desconocido')}"
        
        return JSONResponse({
            "success": True,
            "message": message,
            "total_matches": result["total_matches"],
            "fetched_at": result["fetched_at"],
            "matches_data": result["data"],  # Incluir los datos de los partidos
            "matches_saved_to": str(filepath),
            "matches_filename": filename,
            "season_summaries": {
                "season_id": season_id,
                "success": season_result.get("success", False),
                "error": season_result.get("error", None),
                "status_code": season_result.get("status_code", None)
            },
            "season_summaries_saved_to": str(season_filepath),
            "season_summaries_filename": season_filename
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener partidos: {str(e)}"
        )


@app.get("/api/competitor-profile/{competitor_id}")
async def get_competitor_profile(competitor_id: str):
    """
    Endpoint para obtener el perfil de un competidor.
    
    Args:
        competitor_id (str): ID del competidor (ej: "sr:competitor:157754")
    
    Returns:
        JSONResponse: Datos del perfil del competidor
    """
    try:
        result = fetch_competitor_profile(competitor_id)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Error desconocido al obtener perfil")
            )
        
        return JSONResponse(result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener perfil: {str(e)}"
        )


@app.post("/api/fetch-daily-summaries")
async def fetch_daily_summaries_endpoint():
    """
    Endpoint para obtener resúmenes diarios de partidos de Sportradar.
    Obtiene los partidos del día actual que han finalizado.
    """
    try:
        # Obtener la fecha actual en formato YYYY-MM-DD
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Obtener configuración
        access_level = DEFAULT_CONFIG.get("sportradar_access_level", "trial")
        language_code = DEFAULT_CONFIG.get("sportradar_language", "en")
        
        # Llamar a la función que obtiene los resúmenes diarios
        result = fetch_daily_summaries(
            date=current_date,
            access_level=access_level,
            language_code=language_code,
            format="json"
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Error desconocido al obtener resúmenes diarios")
            )
        
        # Guardar los datos en un archivo JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"daily_summaries_{timestamp}.json"
        filepath = DATA_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result["data"], f, indent=2, ensure_ascii=False)
        
        return JSONResponse({
            "success": True,
            "message": f"Se obtuvieron {result['total_matches']} partidos para la fecha {current_date}",
            "total_matches": result["total_matches"],
            "date": result["date"],
            "fetched_at": result["fetched_at"],
            "matches_data": result["data"],  # Incluir los datos de los partidos
            "matches_saved_to": str(filepath),
            "matches_filename": filename
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener resúmenes diarios: {str(e)}"
        )


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/favicon.ico")
async def favicon():
    """
    Basic favicon endpoint to avoid 404s in the browser.
    Returns an empty icon response (you can replace with a real favicon later).
    """
    return Response(content=b"", media_type="image/x-icon")


def _scan_results_root(root: Path, storage: str, max_matches: int = 30) -> List[Dict[str, Any]]:
    """
    Scan a results root directory (web/results or results) and return
    basic info about matches that have final_bet_decision files.
    """
    matches: List[Dict[str, Any]] = []

    if not root.exists() or not root.is_dir():
        return matches

    # Sort match directories by modification time (newest first)
    try:
        match_dirs = sorted(
            [p for p in root.iterdir() if p.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except Exception:
        return matches

    for match_dir in match_dirs:
        # Each match dir should contain one or more analysis_date subdirs
        try:
            date_dirs = [d for d in match_dir.iterdir() if d.is_dir()]
        except Exception:
            continue

        if not date_dirs:
            continue

        # Pick the latest analysis date for this match
        date_dirs_sorted = sorted(date_dirs, key=lambda d: d.name, reverse=True)
        analysis_dir = date_dirs_sorted[0]
        report_dir = analysis_dir / "reports"

        if not report_dir.exists() or not report_dir.is_dir():
            continue

        # Try to read tournament name from tournament_report.md
        tournament_name = ""
        try:
            tournament_file = report_dir / "tournament_report.md"
            if tournament_file.exists():
                keywords = [
                    "challenger",
                    "cup",
                    "open",
                    "masters",
                    "atp",
                    "wta",
                    "copa",
                    "finals",
                ]
                fallback_name = ""

                with open(tournament_file, "r", encoding="utf-8") as f:
                    for line in f:
                        stripped = line.strip()
                        if not stripped:
                            continue
                        # Remove markdown heading markers
                        if stripped.startswith("#"):
                            stripped = stripped.lstrip("#").strip()

                        # Heuristic: intentar extraer sólo el nombre del torneo
                        lower = stripped.lower()

                        # 1) Si aparece la palabra "torneo", usar lo que viene después
                        candidate = None
                        torneo_idx = lower.find("torneo ")
                        if torneo_idx != -1:
                            candidate = stripped[torneo_idx + len("torneo ") :]

                        # 2) Si no hay "torneo", usar patrones "del / de la / de los / de"
                        if candidate is None:
                            start_idx = -1
                            for prefix in ["del ", "de la ", "de los ", "de "]:
                                i = lower.find(prefix)
                                if i != -1:
                                    start_idx = i + len(prefix)
                                    break

                            candidate = stripped[start_idx:] if start_idx != -1 else stripped

                        # 3) Cortar en conectores típicos que suelen venir después del nombre
                        #    (y, en, para, que, contexto, etc.) sin perder el año
                        candidate = re.split(r"\s+(?:y|en|para|que|contexto)\b", candidate, 1)[0]
                        # 4) Cortar en puntuación fuerte si aparece algo más después
                        candidate = re.split(r"[.,-]", candidate, 1)[0]

                        candidate = candidate.strip(" .,-")
                        if not candidate:
                            continue

                        # 4) Decidir si este candidate parece un buen nombre de torneo
                        cand_lower = candidate.lower()
                        has_year = any(ch.isdigit() for ch in candidate)
                        has_keyword = any(kw in cand_lower for kw in keywords)

                        if has_keyword or has_year:
                            tournament_name = candidate
                            break

                        # Guardar como posible fallback por si no encontramos nada mejor
                        if not fallback_name:
                            fallback_name = candidate

                if not tournament_name:
                    tournament_name = fallback_name
        except Exception:
            tournament_name = ""

        # Look for up to 5 final_bet_decision*.md files OR if cancelled
        try:
            final_files = sorted(report_dir.glob("final_bet_decision*.md"))
        except Exception:
            continue
        
        # Check status first to decide if we include it even without final files
        status = "completed"
        status_file = analysis_dir / "status.json"
        if status_file.exists():
            try:
                with open(status_file, "r", encoding="utf-8") as f:
                    status_data = json.load(f)
                    status = status_data.get("status", "completed")
            except Exception:
                pass

        # If cancelled, include even if no final files (so it shows up in history)
        if not final_files and status != "cancelled":
            continue

        # Derive basic match info from directory name
        dir_name = match_dir.name
        match_label = dir_name
        timestamp = ""
        # status variable is already set above

        if "_" in dir_name:
            # Expected pattern: "Player1 vs Player2_YYYYMMDD_XXXXXX" (CLI) or similar
            try:
                base_label, timestamp = dir_name.rsplit("_", 1)
            except ValueError:
                base_label = dir_name
                timestamp = ""

            # Remove trailing date suffix (_YYYYMMDD) if present so the label is only "Player1 vs Player2"
            m = re.match(r"^(.*)_([0-9]{8})$", base_label)
            if m:
                match_label = m.group(1)
            else:
                match_label = base_label

        if " vs " in match_label:
            player1, player2 = match_label.split(" vs ", 1)
        else:
            player1, player2 = match_label, ""

        matches.append(
            {
                "storage": storage,  # "web" or "cli"
                "match_dir": dir_name,
                "analysis_date": analysis_dir.name,
                "match_label": match_label,
                "player1": player1,
                "player2": player2,
                "tournament": tournament_name,
                "timestamp": timestamp,
                "status": status,
                "final_files": [f.name for f in final_files[:5]],
            }
        )

        if len(matches) >= max_matches:
            break

    return matches


@app.get("/api/predicted-matches")
async def get_predicted_matches():
    """
    List recent matches that already have final_bet_decision reports.
    It scans both web/results (web runs) and results (CLI runs).
    """
    try:
        web_matches = _scan_results_root(WEB_RESULTS_DIR, storage="web")
        cli_matches = _scan_results_root(CLI_RESULTS_DIR, storage="cli")

        # Combine and sort by a rough "recency" heuristic using timestamp/analysis_date
        all_matches = web_matches + cli_matches

        def sort_key(m: Dict[str, Any]):
            return f"{m.get('analysis_date','')}_{m.get('timestamp','')}"

        all_matches_sorted = sorted(all_matches, key=sort_key, reverse=True)

        return JSONResponse(
            {
                "success": True,
                "matches": all_matches_sorted,
                "total": len(all_matches_sorted),
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener partidos predichos: {str(e)}",
        )


@app.get("/api/predicted-match-details")
async def get_predicted_match_details(
    storage: str, match_dir: str, analysis_date: str
):
    """
    Return up to 5 final_bet_decision*.md files for a given stored match.

    Args:
        storage: "web" or "cli" (results root)
        match_dir: directory name of the match (e.g. "A vs B_20251123_154304")
        analysis_date: analysis date folder (e.g. "2025-11-23")
    """
    try:
        if storage not in {"web", "cli"}:
            raise HTTPException(status_code=400, detail="storage debe ser 'web' o 'cli'")

        base_dir = WEB_RESULTS_DIR if storage == "web" else CLI_RESULTS_DIR
        target_dir = base_dir / match_dir / analysis_date / "reports"

        if not target_dir.exists() or not target_dir.is_dir():
            raise HTTPException(
                status_code=404,
                detail="No se encontró el directorio de reports para este partido",
            )

        # Try to read final_response.md
        final_response_content = ""
        try:
            final_response_file = target_dir / "final_response.md"
            if final_response_file.exists():
                with open(final_response_file, "r", encoding="utf-8") as f:
                    final_response_content = f.read()
        except Exception:
            pass

        # Collect up to 5 final_bet_decision*.md files
        final_files = sorted(target_dir.glob("final_bet_decision*.md"))
        
        # Check status
        status = "completed"
        status_file = base_dir / match_dir / analysis_date / "status.json"
        if status_file.exists():
            try:
                with open(status_file, "r", encoding="utf-8") as f:
                    status_data = json.load(f)
                    status = status_data.get("status", "completed")
            except Exception:
                pass

        if not final_files and status != "cancelled":
            raise HTTPException(
                status_code=404,
                detail="No se encontraron archivos final_bet_decision para este partido",
            )

        predictions = []
        for fpath in final_files[:5]:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue

            # Try to use the first non-empty line as title
            title = ""
            for line in content.splitlines():
                stripped = line.strip()
                if stripped:
                    # Remove leading markdown heading markers
                    if stripped.startswith("#"):
                        stripped = stripped.lstrip("#").strip()
                    title = stripped
                    break

            predictions.append(
                {
                    "filename": fpath.name,
                    "title": title or fpath.name,
                    "content": content,
                }
            )

        if not predictions and status != "cancelled":
            raise HTTPException(
                status_code=404,
                detail="No se pudieron leer las predicciones para este partido",
            )

        # Recreate basic match info from match_dir name
        match_label = match_dir
        timestamp = ""
        if "_" in match_dir:
            try:
                match_label, timestamp = match_dir.rsplit("_", 1)
            except ValueError:
                match_label = match_dir

        if " vs " in match_label:
            player1, player2 = match_label.split(" vs ", 1)
        else:
            player1, player2 = match_label, ""

        return JSONResponse(
            {
                "success": True,
                "match": {
                    "storage": storage,
                    "match_dir": match_dir,
                    "analysis_date": analysis_date,
                    "match_label": match_label,
                    "player1": player1,
                    "player2": player2,
                    "timestamp": timestamp,
                    "status": status,
                },
                "predictions": predictions,
                "final_response": final_response_content,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener detalles de la predicción: {str(e)}",
        )


@app.post("/api/calculate-earnings")
async def calculate_earnings_endpoint():
    """Trigger earnings calculation."""
    try:
        manager = EarningsManager()
        result = await manager.calculate_earnings()
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/get-earnings")
async def get_earnings_endpoint():
    """Get earnings history."""
    try:
        manager = EarningsManager()
        data = manager._load_earnings()
        return JSONResponse({"success": True, "data": data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

