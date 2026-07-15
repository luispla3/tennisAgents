import re
import requests
from bs4 import BeautifulSoup

js = requests.get(
    "https://www.tennisabstract.com/jsfrags/StanWawrinka.js",
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=15,
).text

match = re.search(r"var player_frag = `([\s\S]*?)`;", js)
frag = match.group(1) if match else ""
soup = BeautifulSoup(frag, "html.parser")

for table_id in ["career-splits", "last52-splits", "head-to-heads"]:
    table = soup.find("table", id=table_id)
    if not table:
        print(f"\n{table_id}: NOT FOUND")
        continue
    rows = table.find_all("tr")
    print(f"\n=== {table_id} ({len(rows)} rows) ===")
    for row in rows[:8]:
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
        print(cells)
