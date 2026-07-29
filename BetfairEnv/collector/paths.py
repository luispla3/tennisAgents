"""Rutas del proyecto y acceso a los scrapers externos."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RUN_DIR = ROOT / ".run"

# Repo tennisAgents: scrapers en tennisAgents/dataflows/
PROJECT_ROOT = ROOT.parent
DATAFLOWS_DIR = (PROJECT_ROOT / "tennisAgents" / "dataflows").resolve()
SCRAPER_PATHS = (
    DATAFLOWS_DIR,
    PROJECT_ROOT.resolve(),
)
_SCRAPER_PACKAGE_PREFIXES = (
    "betfair_scraper",
    "flashscore_scraper",
)


def _module_file(module: object) -> Path | None:
    origin = getattr(module, "__file__", None)
    if not origin:
        return None
    try:
        return Path(origin).resolve()
    except OSError:
        return None


def _is_repo_scraper_module(module: object) -> bool:
    path = _module_file(module)
    if path is None:
        return False
    try:
        path.relative_to(DATAFLOWS_DIR)
        return True
    except ValueError:
        return False


def _purge_foreign_scraper_modules() -> list[str]:
    """Elimina de sys.modules scrapers que no vienen del repo."""
    removed: list[str] = []
    for name in list(sys.modules):
        if not any(
            name == prefix or name.startswith(f"{prefix}.")
            for prefix in _SCRAPER_PACKAGE_PREFIXES
        ):
            continue
        module = sys.modules.get(name)
        if module is None:
            continue
        if _is_repo_scraper_module(module):
            continue
        # Sin __file__ (namespace) o fuera de dataflows → expulsar.
        del sys.modules[name]
        removed.append(name)
    return removed


def ensure_scraper_paths() -> None:
    """
    Deja los scrapers del repo por delante de site-packages.

    Algunos imports (p.ej. via tennisAgents) pueden reordenar sys.path y hacer
    que un paquete incompleto `betfair_scraper` de site-packages opaque al local.
    Además purga módulos ya cargados desde fuera de tennisAgents/dataflows.
    """
    for path in reversed(SCRAPER_PATHS):
        path_str = str(path)
        while path_str in sys.path:
            sys.path.remove(path_str)
        sys.path.insert(0, path_str)
    _purge_foreign_scraper_modules()


ensure_scraper_paths()
