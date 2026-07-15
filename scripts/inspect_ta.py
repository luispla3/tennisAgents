import re
import requests
from bs4 import BeautifulSoup

url = "https://www.tennisabstract.com/cgi-bin/player.cgi?p=StanWawrinka"
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
html = r.text
print("Status:", r.status_code, "len:", len(html))

for var in ["fullname", "currentrank", "peakrank", "elo_rating", "elo_rank", "country", "hand", "dob"]:
    m = re.search(rf"var {var} = '([^']*)';", html)
    print(f"{var}:", m.group(1) if m else "NOT FOUND")

soup = BeautifulSoup(html, "html.parser")
tables = soup.find_all("table")
print("Tables:", len(tables))
for i, t in enumerate(tables[:5]):
    rows = t.find_all("tr")
    print(f"Table {i}: {len(rows)} rows")
    if rows:
        print("  Header:", [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])[:10]])
        if len(rows) > 1:
            print("  Row1:", [c.get_text(strip=True) for c in rows[1].find_all("td")[:10]])

# Check id/class of results table
for t in tables:
    tid = t.get("id", "")
    cls = t.get("class", [])
    rows = t.find_all("tr")
    if len(rows) > 5:
        print(f"Big table id={tid} class={cls} rows={len(rows)}")
