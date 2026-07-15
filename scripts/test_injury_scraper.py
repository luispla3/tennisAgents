import importlib.util
import sys
import types

ROOT = "."
sys.path.insert(0, ROOT)


def load_module(name: str, path: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Stub package hierarchy to avoid dataflows/__init__.py (langchain dependency)
for pkg in [
    "tennisAgents",
    "tennisAgents.dataflows",
    "tennisAgents.dataflows.flashscore_scraper",
    "tennisAgents.dataflows.match_filters",
]:
    if pkg not in sys.modules:
        sys.modules[pkg] = types.ModuleType(pkg)

load_module("tennisAgents.dataflows.match_filters", "tennisAgents/dataflows/match_filters.py")
client_mod = load_module(
    "tennisAgents.dataflows.flashscore_scraper.client",
    "tennisAgents/dataflows/flashscore_scraper/client.py",
)
parser_mod = load_module(
    "tennisAgents.dataflows.flashscore_scraper.parser",
    "tennisAgents/dataflows/flashscore_scraper/parser.py",
)
scraper_init = load_module(
    "tennisAgents.dataflows.flashscore_scraper",
    "tennisAgents/dataflows/flashscore_scraper/__init__.py",
)
match_live = load_module(
    "tennisAgents.dataflows.match_live_utils",
    "tennisAgents/dataflows/match_live_utils.py",
)
injuries_mod = load_module(
    "tennisAgents.dataflows.flashscore_scraper.injuries",
    "tennisAgents/dataflows/flashscore_scraper/injuries.py",
)

report = injuries_mod.format_injury_reports("Van De Zandschulp B.", "Vallejo D.")
print(report)
