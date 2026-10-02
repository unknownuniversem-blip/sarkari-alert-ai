import urllib.request
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime

FEEDS = [
    "https://www.freejobalert.com/feed",
]

def clean_text(text):
    return re.sub(r'<[^>]+>', '', text or '').strip()

def run_scraper():
    # Load existing database as base
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = { "jobs": [], "admit": [], "results": [], "answerkey": [], "syllabus": [], "admission": [], "certificate": [] }

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    for feed_url in FEEDS:
        try:
            req = urllib.request.Request(feed_url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                root = ET.fromstring(response.read())
                for item in root.findall('.//item')[:25]:
                    title = clean_text(item.find('title').text)
                    link = clean_text(item.find('link').text)
                    lower = title.lower()

                    # Deduce section
                    target_bucket = "jobs"
                    if "result" in lower or "marks" in lower or "scorecard" in lower:
                        target_bucket = "results"
                    elif "admit card" in lower or "hall ticket" in lower or "exam city" in lower:
                        target_bucket = "admit"
                    elif "answer key" in lower or "key challenge" in lower:
                        target_bucket = "answerkey"
                    elif "syllabus" in lower or "pattern" in lower:
                        target_bucket = "syllabus"
                    elif "admission" in lower or "entrance" in lower or "counseling" in lower:
                        target_bucket = "admission"

                    # Deduce organization badge
                    org = "Govt"
                    for o in ["SSC", "UPSC", "UPPSC", "Railway", "RRB", "High Court", "Bank", "Police", "NTA", "BPSC", "UPSSSC"]:
                        if o.lower() in lower:
                            org = o
                            break

                    entry = {
                        "title": title,
                        "org": org,
                        "date": datetime.now().strftime("%b %Y"),
                        "link": link
                    }

                    # Prepend if unique
                    existing_titles = [x["title"] for x in data.get(target_bucket, [])]
                    if title not in existing_titles:
                        data.setdefault(target_bucket, []).insert(0, entry)

        except Exception as e:
            print(f"Feed error: {e}")

    # Keep lists capped at 25 most recent notices per bucket
    for k in data:
        data[k] = data[k][:25]

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("✅ data.json updated with multi-category Sarkari notices!")

if __name__ == '__main__':
    run_scraper()
