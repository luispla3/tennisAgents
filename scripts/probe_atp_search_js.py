import re
import requests

html = requests.get(
    "https://edx.atptour.com/en/h2h",
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30,
).text

# Extract searchPlayers function body
idx = html.find("searchPlayers")
while idx != -1:
    snippet = html[max(0, idx - 100): idx + 400]
    if "function" in snippet or "=>" in snippet or "http" in snippet or "/-/" in snippet:
        print("---")
        print(snippet)
    idx = html.find("searchPlayers", idx + 1)

# Look for find/byname usage context
for m in re.finditer(r".{0,120}find/byname.{0,120}", html):
    print("\nFIND:", m.group(0))
