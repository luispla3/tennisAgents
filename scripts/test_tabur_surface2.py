import importlib.util, sys, types
sys.path.insert(0, ".")
for pkg in ["tennisAgents", "tennisAgents.dataflows"]:
    sys.modules.setdefault(pkg, types.ModuleType(pkg))
spec = importlib.util.spec_from_file_location("ta", "tennisAgents/dataflows/tennis_abstract_utils.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

for surface in ["clay", "Clay", "arcilla", "Gstaad", "hard", ""]:
    print("\n=== surface", repr(surface), "===")
    r = mod.format_surface_report("Tabur", surface)
    print(r[:400])

for name in ["Tabur C.", "C. Tabur", "Clement Tabur", "Tabur"]:
    print("\n=== name", name, "->", mod.resolve_player_name(name))
    print(mod.format_surface_report(name, "clay")[:300])
