import urllib.request
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime

SOURCES = [
    {"name": "FreeJobAlert", "url": "https://www.freejobalert.com/feed"},
]

OFFICIAL_DOMAINS = [
    "gov.in", "nic.in", "ac.in", "edu.in", "org.in", "nta.ac.in", "ibps.in",
    "sbi.co.in", "rbi.org.in", "du.ac.in", "bhu.ac.in", "ignou.ac.in",
    "allahabadhighcourt.in", "bpsc.bih.nic.in", "upsssc.gov.in", "uppbpb.gov.in"
]

def clean_text(text):
    return re.sub(r'<[^>]+>', '', text or '').strip()

def resolve_official_destination(title, source_url):
    lower = title.lower()
    
    # Banking Portals
    if "ibps" in lower:
        return "https://www.ibps.in", "https://www.ibps.in"
    elif "sbi" in lower and ("clerk" in lower or "po" in lower or "specialist" in lower):
        return "https://sbi.co.in/careers", "https://sbi.co.in"
    elif "rbi" in lower:
        return "https://opportunities.rbi.org.in", "https://rbi.org.in"
    elif "nabard" in lower:
        return "https://www.nabard.org/careers", "https://www.nabard.org"

    # Universities & Admission Portals
    elif "cuet" in lower:
        return "https://cuet.nta.nic.in", "https://nta.ac.in"
    elif "delhi university" in lower or "du admission" in lower:
        return "https://admission.uod.ac.in", "https://du.ac.in"
    elif "bhu" in lower or "banaras hindu" in lower:
        return "https://bhu.ac.in", "https://bhu.ac.in"
    elif "ignou" in lower:
        return "https://ignouadmission.samarth.edu.in", "https://ignou.ac.in"
    elif "neet" in lower:
        return "https://neet.nta.nic.in", "https://nta.ac.in"

    # Standard Boards
    elif "ssc" in lower:
        return "https://ssc.gov.in", "https://ssc.gov.in"
    elif "railway" in lower or "rrb" in lower or "rrc" in lower:
        return "https://rrbapply.gov.in", "https://indianrailways.gov.in"
    elif "upsc" in lower:
        return "https://upsc.gov.in", "https://upsconline.nic.in"
    elif "up police" in lower or "uppbpb" in lower:
        return "https://uppbpb.gov.in", "https://uppbpb.gov.in"
    elif "high court" in lower:
        return "https://allahabadhighcourt.in", "https://allahabadhighcourt.in"

    for dom in OFFICIAL_DOMAINS:
        if dom in source_url.lower():
            return source_url, source_url

    return source_url, source_url

def extract_metadata(title):
    lower = title.lower()
    org = "Govt Organization"

    # Recognized entities
    for o in ["IBPS", "SBI", "RBI", "NABARD", "Bank", "DU", "BHU", "IGNOU", "CUET", "NTA", "SSC", "UPSC", "UP Police", "Railway", "RRB", "High Court", "BPSC", "UPSSSC"]:
        if o.lower() in lower:
            org = o
            break

    category = "jobs"
    if any(k in lower for k in ["result", "marks", "cutoff", "merit", "scorecard"]):
        category = "results"
    elif any(k in lower for k in ["admit card", "hall ticket", "call letter", "exam city"]):
        category = "admit"
    elif any(k in lower for k in ["answer key", "key challenge"]):
        category = "answerkey"
    elif any(k in lower for k in ["admission", "entrance", "counseling", "seat allocation", "cuet"]):
        category = "admission"

    vac_match = re.search(r'(\d+[\d,]*)\s*(posts|vacancies|post)', lower)
    total_posts = (vac_match.group(1) + " Posts") if vac_match else "Check Notice"

    return org, category, total_posts

def run():
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            db = json.load(f)
    except:
        db = {"jobs": [], "admit": [], "results": [], "admission": [], "answerkey": []}

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    now_str = datetime.now().strftime("%B %d, %Y")

    for src in SOURCES:
        try:
            req = urllib.request.Request(src["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                root = ET.fromstring(response.read())
                items = root.findall('.//item')[:30]

                for item in items:
                    title = clean_text(item.find('title').text)
                    source_url = clean_text(item.find('link').text)
                    if not title or not source_url:
                        continue

                    org, category, total_posts = extract_metadata(title)
                    slug = re.sub(r'[^a-zA-Z0-9]+', '-', title[:45].lower()).strip('-')

                    existing_slugs = [x.get("id") for x in db.get(category, [])]
                    if slug in existing_slugs:
                        continue

                    apply_url, official_site = resolve_official_destination(title, source_url)

                    entry = {
                        "id": slug,
                        "title": title,
                        "date": f"Post Date: {now_str}",
                        "org": org,
                        "total_posts": total_posts,
                        "intro": f"<b>{org}</b> has officially announced <b>{title}</b>. All interested candidates can verify qualifications, dates, and direct links below.",
                        "dates": "• Application Window : <b>Active / As per Schedule</b><br>• Last Date : <b>Check Official Notice PDF</b><br>• Exam / Admit Card : <b>To be announced</b>",
                        "fee": "• Application Fee : <b>As per Official Notification</b><br>• Payment Mode : <b>Online Gateway</b>",
                        "age": "• Minimum Age : <b>18–20 Years</b><br>• Maximum Age : <b>Post-specific</b> (Relaxation as per rules)",
                        "qualification": "• Check the official recruitment notice PDF for post-wise degree, diploma, or certificate criteria.",
                        "vacancies_detail": f"• {total_posts} as per advertisement notice.",
                        "links": {
                            "apply": apply_url,
                            "notice": apply_url,
                            "syllabus": official_site,
                            "official": official_site
                        }
                    }

                    db.setdefault(category, []).insert(0, entry)
        except Exception as e:
            print(f"Scrape warning: {e}")

    for k in db:
        db[k] = db[k][:25]

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    print("✅ Banking and University updates merged!")

if __name__ == '__main__':
    run()
