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

cases = [
    ("Justo G. I.", "Guido Ivan Justo", "GuidoIvanJusto"),
    ("Faria J.", "Jaime Faria", None),
    ("Wawrinka S.", "Stan Wawrinka", None),
    ("Collignon R.", "Raphael Collignon", None),
    ("Sonego L.", "Lorenzo Sonego", None),
    ("De Jong J.", "Jesper De Jong", None),
]

for input_name, expected, expected_slug in cases:
    resolved = mod.resolve_player_name(input_name)
    slug = mod._slug(resolved)
    ok = resolved == expected
    print(f"{'OK' if ok else 'FAIL'} {input_name:15} -> {resolved:20} slug={slug}")
    if expected_slug:
        print(f"     slug expected {expected_slug}, got {slug}")
