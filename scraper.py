import urllib.request
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime

# Aggregates official RSS feeds and government notification boards
FEEDS = [
    {"url": "https://www.freejobalert.com/feed", "default_org": "Govt Exam"},
]

def fetch_and_parse():
    items = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    for feed in FEEDS:
        try:
            req = urllib.request.Request(feed["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                content = response.read()
                root = ET.fromstring(content)
                for item in root.findall('.//item')[:20]:
                    title = item.find('title').text or ""
                    link = item.find('link').text or ""
                    
                    # Clean clean HTML tags
                    title = re.sub(r'<[^>]+>', '', title).strip()

                    # Deduce category
                    cat = "jobs"
                    lower_t = title.lower()
                    if "result" in lower_t or "marks" in lower_t or "merit" in lower_t:
                        cat = "results"
                    elif "admit card" in lower_t or "hall ticket" in lower_t or "call letter" in lower_t:
                        cat = "admit"

                    # Deduce organization
                    org = "Govt"
                    for o in ["SSC", "UPSC", "UPPSC", "Railway", "RRB", "High Court", "Bank", "Police", "NTA"]:
                        if o.lower() in lower_t:
                            org = o
                            break

                    items.append({
                        "category": cat,
                        "title": title,
                        "link": link,
                        "org": org,
                        "date": datetime.now().strftime("%b %Y")
                    })
        except Exception as e:
            print(f"Feed error: {e}")

    if not items:
        print("No new feeds retrieved. Retaining existing records.")
        return

    # Categorize into JSON
    categorized = {"jobs": [], "admit": [], "results": []}
    for it in items:
        categorized[it["category"]].append({
            "title": it["title"],
            "org": it["org"],
            "date": it["date"],
            "link": it["link"]
        })

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(categorized, f, indent=2, ensure_ascii=False)
    print("✅ data.json refreshed successfully with live notices!")

if __name__ == '__main__':
    fetch_and_parse()
