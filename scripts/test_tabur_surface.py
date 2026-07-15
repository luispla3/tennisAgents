import sys
sys.path.insert(0, ".")

from tennisAgents.dataflows.tennis_abstract_utils import (
    resolve_player_name,
    fetch_player_data,
    format_surface_report,
    format_recent_matches_report,
)

names = ["Tabur", "Tabur A.", "A. Tabur", "Andrej Tabur"]
for name in names:
    try:
        resolved = resolve_player_name(name)
        print(f"\n=== {name!r} -> {resolved!r} ===")
        data = fetch_player_data(name)
        print("found", data.get("found"), "recent", len(data.get("recent_matches", [])))
        clay_recent = [r for r in data.get("recent_matches", []) if r.get("Surface", "").lower() == "clay"][:5]
        print("clay recent count", len([r for r in data.get("recent_matches", []) if r.get("Surface", "").lower() == "clay"]))
        if clay_recent:
            print("sample clay row keys", clay_recent[0].keys())
            print("sample clay row", clay_recent[0])
        career = [r for r in data.get("career_splits", []) if "clay" in r.get("Split", "").lower()]
        print("career clay splits", career[:2])
        print("--- surface report clay ---")
        print(format_surface_report(name, "clay")[:1200])
    except Exception as exc:
        print(f"ERROR {name}: {exc}")
