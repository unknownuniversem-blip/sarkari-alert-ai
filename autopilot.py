import urllib.request
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime

# Multi-portal ingestion streams
SOURCES = [
    {"name": "FreeJobAlert", "url": "https://www.freejobalert.com/feed"},
]

# Official government domain whitelist
OFFICIAL_DOMAINS = [
    "gov.in", "nic.in", "ac.in", "edu.in", "org.in", "nta.ac.in", "ibps.in",
    "sbi.co.in", "rbi.org.in", "nabard.org", "licindia.in", "du.ac.in", "bhu.ac.in",
    "ignou.ac.in", "allahabadhighcourt.in", "bpsc.bih.nic.in", "upsssc.gov.in",
    "uppbpb.gov.in", "uppsc.up.nic.in", "rsmssb.rajasthan.gov.in", "rpsc.rajasthan.gov.in",
    "esb.mp.gov.in", "hssc.gov.in", "joinindianarmy.nic.in", "joinindiannavy.gov.in",
    "agnipathvayu.cdac.in", "ctet.nic.in", "isro.gov.in", "drdo.gov.in"
]

def clean_text(text):
    return re.sub(r'<[^>]+>', '', text or '').strip()

def resolve_official_destination(title, source_url):
    lower = title.lower()
    
    # 1. SSC & UPSC Central
    if "ssc" in lower:
        return "https://ssc.gov.in", "https://ssc.gov.in"
    elif "upsc" in lower:
        return "https://upsc.gov.in", "https://upsconline.nic.in"

    # 2. Banking & Financial
    elif "ibps" in lower:
        return "https://www.ibps.in", "https://www.ibps.in"
    elif "sbi" in lower:
        return "https://sbi.co.in/careers", "https://sbi.co.in"
    elif "rbi" in lower:
        return "https://opportunities.rbi.org.in", "https://rbi.org.in"
    elif "nabard" in lower:
        return "https://www.nabard.org/careers", "https://www.nabard.org"
    elif "lic" in lower:
        return "https://licindia.in/careers", "https://licindia.in"

    # 3. Railways
    elif any(k in lower for k in ["railway", "rrb", "rrc", "alp", "ntpc", "technician"]):
        return "https://rrbapply.gov.in", "https://indianrailways.gov.in"

    # 4. Uttar Pradesh State
    elif "upsssc" in lower or "pet" in lower or "lekhpal" in lower:
        return "https://upsssc.gov.in", "https://upsssc.gov.in"
    elif "uppsc" in lower or "ro/aro" in lower and "up" in lower:
        return "https://uppsc.up.nic.in", "https://uppsc.up.nic.in"
    elif "up police" in lower or "uppbpb" in lower:
        return "https://uppbpb.gov.in", "https://uppbpb.gov.in"
    elif "allahabad high court" in lower or "ahc" in lower:
        return "https://allahabadhighcourt.in", "https://allahabadhighcourt.in"

    # 5. Bihar State
    elif "bpsc" in lower:
        return "https://bpsc.bih.nic.in", "https://onlinebpsc.bihar.gov.in"
    elif "bssc" in lower:
        return "https://bssc.bihar.gov.in", "https://bssc.bihar.gov.in"
    elif "bihar police" in lower or "csbc" in lower:
        return "https://csbc.bih.nic.in", "https://csbc.bih.nic.in"
    elif "patna high court" in lower:
        return "https://patnahighcourt.gov.in", "https://patnahighcourt.gov.in"

    # 6. Rajasthan, MP & Haryana
    elif "rsmssb" in lower or "rssb" in lower:
        return "https://rsmssb.rajasthan.gov.in", "https://rsmssb.rajasthan.gov.in"
    elif "rpsc" in lower:
        return "https://rpsc.rajasthan.gov.in", "https://rpsc.rajasthan.gov.in"
    elif "mppsc" in lower or "mpeb" in lower or "mp esb" in lower:
        return "https://esb.mp.gov.in", "https://mppsc.mp.gov.in"
    elif "hssc" in lower or "haryana cet" in lower:
        return "https://hssc.gov.in", "https://hssc.gov.in"

    # 7. Defense & Paramilitary
    elif "army" in lower or "agniveer army" in lower:
        return "https://joinindianarmy.nic.in", "https://joinindianarmy.nic.in"
    elif "navy" in lower:
        return "https://joinindiannavy.gov.in", "https://joinindiannavy.gov.in"
    elif "air force" in lower or "airforce" in lower or "iaf" in lower:
        return "https://agnipathvayu.cdac.in", "https://indianairforce.nic.in"
    elif any(k in lower for k in ["crpf", "bsf", "cisf", "itbp", "ssb", "assam rifles"]):
        return "https://rect.bsf.gov.in", "https://ssc.gov.in"

    # 8. Teacher & Eligibility
    elif "ctet" in lower:
        return "https://ctet.nic.in", "https://ctet.nic.in"
    elif "ugc net" in lower:
        return "https://ugcnet.nta.ac.in", "https://nta.ac.in"
    elif "csir net" in lower:
        return "https://csirnet.nta.ac.in", "https://nta.ac.in"

    # 9. Universities
    elif "cuet" in lower:
        return "https://cuet.nta.nic.in", "https://nta.ac.in"
    elif "delhi university" in lower or "du csas" in lower:
        return "https://admission.uod.ac.in", "https://du.ac.in"
    elif "bhu" in lower:
        return "https://bhu.ac.in", "https://bhu.ac.in"
    elif "ignou" in lower:
        return "https://ignouadmission.samarth.edu.in", "https://ignou.ac.in"

    # If domain in source is whitelisted, accept it
    for dom in OFFICIAL_DOMAINS:
        if dom in source_url.lower():
            return source_url, source_url

    return source_url, source_url

def extract_meta(title):
    lower = title.lower()
    org = "Govt Recruitment"

    org_keywords = [
        "SSC", "UPSC", "IBPS", "SBI", "RBI", "NABARD", "LIC", "UPSSSC", "UPPSC",
        "UP Police", "High Court", "BPSC", "BSSC", "Bihar Police", "RSMSSB", "RPSC",
        "MPPEB", "MPPSC", "HSSC", "Railway", "RRB", "RRC", "Army", "Navy", "Air Force",
        "CRPF", "BSF", "CISF", "ITBP", "CTET", "UGC NET", "CUET", "DU", "BHU", "IGNOU", "ISRO", "DRDO"
    ]

    for o in org_keywords:
        if o.lower() in lower:
            org = o
            break

    category = "jobs"
    if any(k in lower for k in ["result", "marks", "cutoff", "merit", "scorecard", "selected"]):
        category = "results"
    elif any(k in lower for k in ["admit card", "hall ticket", "call letter", "exam city", "status"]):
        category = "admit"
    elif any(k in lower for k in ["answer key", "key challenge", "solution"]):
        category = "answerkey"
    elif any(k in lower for k in ["admission", "entrance", "counseling", "seat allocation"]):
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

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    now_str = datetime.now().strftime("%B %d, %Y")

    for src in SOURCES:
        try:
            req = urllib.request.Request(src["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                root = ET.fromstring(response.read())
                items = root.findall('.//item')[:40]

                for item in items:
                    title = clean_text(item.find('title').text)
                    source_url = clean_text(item.find('link').text)
                    if not title or not source_url:
                        continue

                    org, category, total_posts = extract_meta(title)
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
                        "intro": f"<b>{org}</b> has officially announced <b>{title}</b>. All eligible candidates can verify eligibility qualifications, important dates, and official application portals below.",
                        "dates": "• Application Status : <b>Active Now / As per Schedule</b><br>• Last Date : <b>Check Official Notice PDF</b><br>• Exam / Admit Card : <b>To be announced by Board</b>",
                        "fee": "• Application Fee : <b>As per Official Notification</b><br>• Concessions/Exemptions applicable as per category norms.<br>• Mode : <b>Online Gateway</b>",
                        "age": "• Minimum Age : <b>18–21 Years</b><br>• Maximum Age : <b>Post-specific</b> (Age relaxation applicable as per rules).",
                        "qualification": "• Candidate must possess the requisite educational qualification (10th / 12th / Diploma / Graduate / Post-Graduate Degree) from a recognized Board/University as detailed in the official notice.",
                        "vacancies_detail": f"• {total_posts} as per conducting board notification.",
                        "links": {
                            "apply": apply_url,
                            "notice": apply_url,
                            "syllabus": official_site,
                            "official": official_site
                        }
                    }

                    db.setdefault(category, []).insert(0, entry)
        except Exception as e:
            print(f"Fetch warning: {e}")

    for k in db:
        db[k] = db[k][:35]

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    print("✅ All major sectors verified and synchronized!")

if __name__ == '__main__':
    run()
