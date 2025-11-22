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

