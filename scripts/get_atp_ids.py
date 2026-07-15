import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "ta",
    Path(__file__).resolve().parents[1] / "tennisAgents" / "dataflows" / "tennis_abstract_utils.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

for name in ["Sonego L.", "Collignon R.", "Lorenzo Sonego", "Raphael Collignon"]:
    p = mod.fetch_player_profile(name)
    print(name, "->", p.get("resolved_name"), "atp_id=", p.get("atp_id"))
