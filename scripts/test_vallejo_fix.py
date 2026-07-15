import importlib.util

spec = importlib.util.spec_from_file_location("ta", "tennisAgents/dataflows/tennis_abstract_utils.py")
ta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ta)

cases = [
    "Vallejo D.",
    "Van De Zandschulp B.",
    "Justo G. I.",
    "Wessels L.",
    "Coppejans K.",
]
for name in cases:
    p = ta.fetch_player_profile(name)
    print(
        f"{name:25} -> {p.get('resolved_name'):30} "
        f"found={p.get('found')} rank={p.get('current_rank')} atp={p.get('atp_id')}"
    )

print("\nH2H test:")
spec2 = importlib.util.spec_from_file_location("h2h", "tennisAgents/dataflows/atp_h2h_utils.py")
h2h = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(h2h)
report = h2h.format_atp_h2h_report("Van De Zandschulp B.", "Vallejo D.")
print(report[:600])
