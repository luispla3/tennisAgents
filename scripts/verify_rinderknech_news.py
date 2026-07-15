import re
import sys

sys.path.insert(0, r"C:\Users\luisp\tennisAgents")
from tennisAgents.dataflows.news_utils import fetch_news_for_match

r = fetch_news_for_match("Tabur", "Rinderknech", "Gstaad", "2026-07-15")
print("TOTAL_LEN", len(r))
print("EMPTY", "Sin resultados" in r or "No se encontraron resultados" in r)

for label in ("Rinderknech", "Tabur", "Gstaad"):
    match = re.search(
        rf"## Noticias sobre '{label}'.*?(?=\n## Noticias sobre '|\Z)",
        r,
        re.S,
    )
    block = match.group(0) if match else ""
    titles = re.findall(r"^\d+\. (.+)$", block, re.M)
    print(f"\n=== {label}: {len(titles)} titulares ===")
    for title in titles[:4]:
        print("-", title[:120])

match_headline = any(
    "Rinderknech" in line and "Tabur" in line
    for line in r.splitlines()
    if re.match(r"^\d+\.", line)
)
print("\nMENCIONA EL PARTIDO Tabur vs Rinderknech:", match_headline)
