import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "tennis_abstract_utils",
    Path(__file__).resolve().parents[1] / "tennisAgents" / "dataflows" / "tennis_abstract_utils.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

print(mod.format_profiles_report("Faria J.", "Wawrinka S."))
print("\n" + "=" * 60 + "\n")
print(mod.format_recent_matches_report("Faria J.", "Wawrinka S.", 5))
print("\n" + "=" * 60 + "\n")
print(mod.format_surface_report("Wawrinka S.", "clay"))
print("\n" + "=" * 60 + "\n")
print(mod.format_head_to_head_report("Faria J.", "Wawrinka S."))
