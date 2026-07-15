import importlib.util, sys, types
sys.path.insert(0, ".")
for pkg in ["tennisAgents", "tennisAgents.dataflows"]:
    sys.modules.setdefault(pkg, types.ModuleType(pkg))

# load tournament_utils
spec_t = importlib.util.spec_from_file_location("tu", "tennisAgents/dataflows/tournament_utils.py")
tu = importlib.util.module_from_spec(spec_t)
sys.modules["tennisAgents.dataflows.tournament_utils"] = tu
spec_t.loader.exec_module(tu)

spec_ta = importlib.util.spec_from_file_location("ta", "tennisAgents/dataflows/tennis_abstract_utils.py")
ta = importlib.util.module_from_spec(spec_ta)
spec_ta.loader.exec_module(ta)

print("Gstaad ->", tu.resolve_tournament_surface("Gstaad"))
print("ATP Gstaad ->", tu.resolve_tournament_surface("ATP - SINGLES: Gstaad (Switzerland), clay"))

# simulate fetch_surface_winrate logic
surface = "Gstaad"
candidates = []
for value in (surface, tu.resolve_tournament_surface(surface)):
    if value and value not in candidates:
        candidates.append(value)
print("candidates", candidates)
for c in candidates:
    r = ta.format_surface_report("Tabur", c)
    print(c, "->", "1stIn" in r, r.splitlines()[0])
