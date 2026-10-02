import urllib.request
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime

# Multi-board notification endpoints
FEEDS = [
    "https://www.freejobalert.com/feed",
]

def clean(text):
    return re.sub(r'<[^>]+>', '', text or '').strip()

def extract_meta_from_title(title):
    lower = title.lower()
    
    # Organization
    org = "Govt"
    for o in ["SSC", "UPSC", "UP Police", "Railway", "RRB", "High Court", "BPSC", "UPSSSC", "NTA", "Bank", "IBPS", "Army", "Navy", "Airforce", "DSSSB", "Teacher"]:
        if o.lower() in lower:
            org = o
            break

    # Category
    category = "jobs"
    if any(k in lower for k in ["result", "marks", "cutoff", "merit"]):
        category = "results"
    elif any(k in lower for k in ["admit card", "hall ticket", "city details", "call letter"]):
        category = "admit"
    elif any(k in lower for k in ["answer key", "key challenge"]):
        category = "answerkey"
    elif any(k in lower for k in ["syllabus", "exam pattern"]):
        category = "syllabus"
    elif any(k in lower for k in ["admission", "entrance", "counseling"]):
        category = "admission"

    # Vacancy count extraction
    vac_match = re.search(r'(\d+[\d,]*)\s*(posts|vacancies|post)', lower)
    total_posts = (vac_match.group(1) + " Posts") if vac_match else "Check Notification"

    return org, category, total_posts

def run_autopilot():
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            db = json.load(f)
    except:
        db = {
            "jobs": [], "admit": [], "results": [], "answerkey": [],
            "documents": [], "admission": [], "iti_jobs": [], "outsourcing": [], "syllabus": []
        }

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    new_count = 0
    now_str = datetime.now().strftime("%B %d, %Y %I:%M %p")

    for feed_url in FEEDS:
        try:
            req = urllib.request.Request(feed_url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                root = ET.fromstring(response.read())
                items = root.findall('.//item')[:30]

                for item in items:
                    title = clean(item.find('title').text)
                    link = clean(item.find('link').text)
                    if not title or not link:
                        continue

                    org, cat, total_posts = extract_meta_from_title(title)
                    slug = re.sub(r'[^a-zA-Z0-9]+', '-', title[:45].lower()).strip('-')

                    # Skip duplicate entries
                    existing_slugs = [x.get("id") for x in db.get(cat, [])]
                    if slug in existing_slugs:
                        continue

                    entry = {
                        "id": slug,
                        "title": title,
                        "date": f"Post Date: {now_str}",
                        "org": org,
                        "total_posts": total_posts,
                        "intro": f"<b>{org}</b> has officially announced <b>{title}</b>. Candidates can check the exam dates, eligibility criteria, and important links below.",
                        "dates": f"• Application Notification : <b>Active Now</b><br>• Last Date : <b>Check Official Notice</b><br>• Exam / Event Date : <b>As per schedule</b><br>• Admit Card : <b>To be notified</b>",
                        "fee": "• General / OBC / EWS : <b>As per official norms</b><br>• SC / ST / PWD : <b>Exempted / Concessional</b><br>• Payment Mode : <b>Online NetBanking, UPI, Debit Card</b>",
                        "age": "• Minimum Age : <b>18 Years</b><br>• Maximum Age : <b>As per Post Rules</b><br>• Age relaxation applicable as per government guidelines.",
                        "links": {
                            "apply": link,
                            "notice": link,
                            "official": link
                        }
                    }

                    db.setdefault(cat, []).insert(0, entry)
                    new_count += 1
        except Exception as e:
            print(f"Feed Fetch Warning: {e}")

    # Keep top 30 items per category
    for k in db:
        db[k] = db[k][:30]

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

    print(f"✅ Autopilot completed! Discovered {new_count} new official updates.")

if __name__ == '__main__':
    run_autopilot()
