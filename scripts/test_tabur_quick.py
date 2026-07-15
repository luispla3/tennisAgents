import importlib.util
import sys
import types

sys.path.insert(0, ".")
for pkg in ["tennisAgents", "tennisAgents.dataflows"]:
    sys.modules.setdefault(pkg, types.ModuleType(pkg))

spec = importlib.util.spec_from_file_location(
    "ta", "tennisAgents/dataflows/tennis_abstract_utils.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

name = "Tabur"
resolved = mod.resolve_player_name(name)
print("resolved", resolved)
data = mod.fetch_player_data(name)
print("found", data.get("found"))
print("recent", len(data.get("recent_matches", [])))
clay = [r for r in data.get("recent_matches", []) if r.get("Surface", "").lower() == "clay"]
print("clay matches", len(clay))
if clay:
    print("first clay", clay[0])
print(mod.format_surface_report(name, "clay")[:1500])
