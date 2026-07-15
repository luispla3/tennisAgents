import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
pkg = types.ModuleType("tennisAgents")
pkg_dataflows = types.ModuleType("tennisAgents.dataflows")
sys.modules["tennisAgents"] = pkg
sys.modules["tennisAgents.dataflows"] = pkg_dataflows

spec = importlib.util.spec_from_file_location(
    "tennisAgents.dataflows.tennis_abstract_utils",
    ROOT / "tennisAgents/dataflows/tennis_abstract_utils.py",
)
mod = importlib.util.module_from_spec(spec)
sys.modules["tennisAgents.dataflows.tennis_abstract_utils"] = mod
spec.loader.exec_module(mod)

candidates = [
    "Justo G.I.",
    "Justo G.",
    "Justo I.",
    "G. Justo",
    "Guido Ivan Justo",
    "Justo Guido I.",
    "Justo G.I",
    "Justo GI.",
    "Justo G I",
    "Justo G",
    "Justo GI",
    "Justo G Ivan",
]

for name in candidates:
    resolved = mod.resolve_player_name(name)
    slug = mod._slug(resolved)
    try:
        profile = mod.fetch_player_profile(name)
        found = profile.get("found")
        rank = profile.get("current_rank", "N/D")
    except Exception as exc:
        found = False
        rank = str(exc)[:60]
    print(f"{name:20} -> {resolved:20} slug={slug:18} found={found} rank={rank}")
