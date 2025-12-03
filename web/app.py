"""
FastAPI server for TennisAgents web application
"""
import sys
from pathlib import Path
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import requests
from datetime import datetime

# Add parent directory to path to import tennisAgents modules
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import Sportradar utilities
from tennisAgents.dataflows.match_live_utils import fetch_live_summaries, fetch_season_summaries, fetch_daily_summaries, get_sportradar_api_key
from tennisAgents.default_config import DEFAULT_CONFIG
from tennisAgents.graph.trading_graph import TennisAgentsGraph

from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import json
import os

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
DATA_DIR = PROJECT_ROOT / "web" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

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
async def run_analysis(request: AnalysisRequest):
    """
    Run the tennis analysis system and stream the results.
    """
    
    async def event_generator():
        try:
            # Setup configuration
            config = DEFAULT_CONFIG.copy()
            config["max_debate_rounds"] = request.research_depth
            config["max_risk_discuss_rounds"] = request.research_depth
            config["quick_think_llm"] = request.shallow_thinker
            config["deep_think_llm"] = request.deep_thinker
            if request.backend_url:
                config["backend_url"] = request.backend_url
            config["llm_provider"] = request.llm_provider.lower()
            
            # For web runs, force results into web/results (separado de la CLI)
            web_results_root = PROJECT_ROOT / "web" / "results"
            web_results_root.mkdir(parents=True, exist_ok=True)
            config["results_dir"] = str(web_results_root)
                
            # Setup results directory
            player_pair = f"{request.player1} vs {request.player2}"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_dir_name = f"{player_pair}_{timestamp}"
            results_dir = Path(config["results_dir"]) / unique_dir_name / request.analysis_date
            results_dir.mkdir(parents=True, exist_ok=True)
            report_dir = results_dir / "reports"
            report_dir.mkdir(parents=True, exist_ok=True)
            log_file = results_dir / "message_tool.log"
            log_file.touch(exist_ok=True)
            
            # Initialize graph
            # Note: TennisAgentsGraph is synchronous, but we run it in a way that we can stream
            # Since graph initialization might take a moment, send a status update
            yield json.dumps({
                "type": "status", 
                "data": {"message": "Initializing analysis graph...", "step": "init"}
            }) + "\n"
            
            graph = TennisAgentsGraph(
                request.analysts, 
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
                request.player1, 
                request.player2, 
                request.analysis_date,
                request.tournament,
                request.wallet_balance
            )
            args = graph.propagator.get_graph_args()
            
            yield json.dumps({
                "type": "status", 
                "data": {"message": f"Starting analysis for {player_pair}...", "step": "started"}
            }) + "\n"

            # Stream the analysis
            # Since graph.stream is a generator, we iterate over it
            for chunk in graph.graph.stream(init_agent_state, **args):
                
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
                    # Guardar en fichero Markdown
                    try:
                        with open(report_dir / "news_report.md", "w", encoding="utf-8") as f:
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
                        with open(report_dir / "players_report.md", "w", encoding="utf-8") as f:
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
                        with open(report_dir / "sentiment_report.md", "w", encoding="utf-8") as f:
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
                        with open(report_dir / "tournament_report.md", "w", encoding="utf-8") as f:
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
                        with open(report_dir / "weather_report.md", "w", encoding="utf-8") as f:
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
                        with open(report_dir / "match_live_report.md", "w", encoding="utf-8") as f:
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

            yield json.dumps({
                "type": "status",
                "data": {"message": "Analysis complete!", "step": "completed"}
            }) + "\n"

        except Exception as e:
            yield json.dumps({
                "type": "error",
                "data": {"message": str(e)}
            }) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/predict", response_class=HTMLResponse)
async def predict(request: Request):
    """Predict page"""
    return templates.TemplateResponse("predict.html", {"request": request})


@app.get("/daily-summaries", response_class=HTMLResponse)
async def daily_summaries(request: Request):
    """Daily summaries page"""
    return templates.TemplateResponse("daily-summaries.html", {"request": request})


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
        
        # Llamar al nuevo endpoint de season summaries
        # Por ahora usamos un season_id placeholder (dará error pero se llama como solicitado)
        access_level = DEFAULT_CONFIG.get("sportradar_access_level", "trial")
        language_code = DEFAULT_CONFIG.get("sportradar_language", "en")
        season_id = "test_season_id"  # Placeholder - dará error pero se llama como solicitado
        
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
        
        # Obtener perfiles de los dos jugadores (IDs vacíos por ahora)
        competitor_id_1 = ""  # Vacío por ahora
        competitor_id_2 = ""  # Vacío por ahora
        
        profile_1 = fetch_competitor_profile(competitor_id_1)
        profile_2 = fetch_competitor_profile(competitor_id_2)
        
        # Guardar los perfiles también
        profiles_data = {
            "player_1": {
                "competitor_id": competitor_id_1,
                "profile": profile_1
            },
            "player_2": {
                "competitor_id": competitor_id_2,
                "profile": profile_2
            },
            "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        profiles_filename = f"competitor_profiles_{timestamp}.json"
        profiles_filepath = DATA_DIR / profiles_filename
        
        with open(profiles_filepath, "w", encoding="utf-8") as f:
            json.dump(profiles_data, f, indent=2, ensure_ascii=False)
        
        # Construir mensaje de respuesta incluyendo información del season summaries
        message = f"Se obtuvieron {result['total_matches']} partidos y se intentaron obtener 2 perfiles de competidores"
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
            "season_summaries_filename": season_filename,
            "profiles": {
                "player_1": {
                    "competitor_id": competitor_id_1,
                    "success": profile_1.get("success", False),
                    "error": profile_1.get("error", None)
                },
                "player_2": {
                    "competitor_id": competitor_id_2,
                    "success": profile_2.get("success", False),
                    "error": profile_2.get("error", None)
                }
            },
            "profiles_saved_to": str(profiles_filepath),
            "profiles_filename": profiles_filename
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

