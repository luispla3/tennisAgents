import re
import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Find in player list
r = requests.get("https://www.tennisabstract.com/mwplayerlist.js", headers=HEADERS, timeout=20)
names = re.findall(r'"\(M\) ([^"]+)"', r.text)
matches = [n for n in names if "justo" in n.lower() or "guido" in n.lower()]
print("Player list matches:", matches)

# Test slugs
for slug in ["GuidoIvanJusto", "GuidoJusto", "IvanJusto", "GJusto", "GuidoIvanJusto"]:
    url = f"https://www.tennisabstract.com/cgi-bin/player.cgi?p={slug}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    m = re.search(r"var fullname = '([^']*)';", resp.text)
    if not m:
        m = re.search(r"var fullname = ([^;]+);", resp.text)
    fullname = m.group(1).strip("'\"") if m else ""
    print(f"{slug}: status={resp.status_code} fullname={fullname or 'NOT FOUND'}")
