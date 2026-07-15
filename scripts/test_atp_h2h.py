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
ta = importlib.util.module_from_spec(spec)
sys.modules["tennisAgents.dataflows.tennis_abstract_utils"] = ta
spec.loader.exec_module(ta)

spec = importlib.util.spec_from_file_location(
    "tennisAgents.dataflows.atp_h2h_utils",
    ROOT / "tennisAgents/dataflows/atp_h2h_utils.py",
)
mod = importlib.util.module_from_spec(spec)
sys.modules["tennisAgents.dataflows.atp_h2h_utils"] = mod
spec.loader.exec_module(mod)

print(mod.format_atp_h2h_report("Collignon R.", "Sonego L."))
print("\n" + "=" * 60 + "\n")
print(mod.format_atp_h2h_report("Borges N.", "Dimitrov G.")[:2500])
