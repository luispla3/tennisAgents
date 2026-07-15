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

name = "Justo G. I."
print("resolved:", mod.resolve_player_name(name))
print(mod.format_profiles_report("Bondioli F.", name))
