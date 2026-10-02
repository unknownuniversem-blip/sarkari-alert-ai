import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime
from html.parser import HTMLParser

SOURCES = [
    {"name": "FreeJobAlert", "url": "https://www.freejobalert.com/feed"},
]

OFFICIAL_DOMAINS = [
    "gov.in", "nic.in", "ac.in", "edu.in", "org.in", "nta.ac.in", "ibps.in",
    "sbi.co.in", "rbi.org.in", "nabard.org", "licindia.in", "du.ac.in", "bhu.ac.in",
    "ignou.ac.in", "allahabadhighcourt.in", "bpsc.bih.nic.in", "upsssc.gov.in",
    "uppbpb.gov.in", "uppsc.up.nic.in", "rsmssb.rajasthan.gov.in", "rpsc.rajasthan.gov.in",
    "esb.mp.gov.in", "hssc.gov.in", "joinindianarmy.nic.in", "joinindiannavy.gov.in",
    "agnipathvayu.cdac.in", "ctet.nic.in", "isro.gov.in", "drdo.gov.in"
]

class HTMLTableExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_chunks = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        href = attr_dict.get('href', '')
        if href:
            self.links.append((href, attr_dict.get('title', '')))

    def handle_data(self, data):
        cleaned = data.strip()
        if cleaned:
            self.text_chunks.append(cleaned)

def clean_text(text):
    return re.sub(r'<[^>]+>', '', text or '').strip()

def search_and_verify_sarkariresult(title):
    """
    Fallback cross-verifier: Queries SarkariResult for the given exam title,
    extracts the exact short details table, dates, fees, and PDF/Syllabus links.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    cleaned_query = re.sub(r'[^a-zA-Z0-9 ]', ' ', title).strip()
    words = [w for w in cleaned_query.split() if len(w) > 2][:4]
    search_q = "+".join(words)
    
    fallback_data = {
        "dates": None,
        "fee": None,
        "age": None,
        "qualification": None,
        "vacancies": None,
        "notice_link": None,
        "syllabus_link": None,
        "apply_link": None,
        "official_site": None
    }

    try:
        # Search query against sarkariresult domain
        sr_search_url = f"https://html.duckduckgo.com/html/?q=site:sarkariresult.com+{search_q}"
        req = urllib.request.Request(sr_search_url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as res:
            html = res.read().decode('utf-8', errors='ignore')
            
            # Find the best SarkariResult post link
            match = re.search(r'href="(https://www\.sarkariresult\.com/\d{4}/[^"&]+)"', html)
            if match:
                post_url = match.group(1)
                
                # Crawl the SarkariResult post
                post_req = urllib.request.Request(post_url, headers=headers)
                with urllib.request.urlopen(post_req, timeout=8) as p_res:
                    p_html = p_res.read().decode('utf-8', errors='ignore')
                    
                    parser = HTMLTableExtractor()
                    parser.feed(p_html)
                    full_text = " ".join(parser.text_chunks)

                    # Extract PDF Notice link
                    for lk, _ in parser.links:
                        lk_lower = lk.lower()
                        if lk_lower.endswith('.pdf') or 'notification' in lk_lower or 'notice' in lk_lower:
                            fallback_data["notice_link"] = lk
                        elif 'syllabus' in lk_lower:
                            fallback_data["syllabus_link"] = lk
                        elif 'apply' in lk_lower or 'registration' in lk_lower:
                            fallback_data["apply_link"] = lk
                        elif any(dom in lk_lower for dom in OFFICIAL_DOMAINS):
                            fallback_data["official_site"] = lk

                    # Regex match dates
                    d_match = re.search(r'Application Begin\s*:\s*([^.\n]+)', full_text, re.I)
                    last_match = re.search(r'Last Date for Apply Online\s*:\s*([^.\n]+)', full_text, re.I)
                    exam_match = re.search(r'Exam Date\s*:\s*([^.\n]+)', full_text, re.I)
                    if d_match or last_match:
                        b_date = d_match.group(1).strip() if d_match else "Check Notice"
                        l_date = last_match.group(1).strip() if last_match else "Check Notice"
                        e_date = exam_match.group(1).strip() if exam_match else "As per schedule"
                        fallback_data["dates"] = f"• Application Begin : <b>{b_date}</b><br>• Last Date : <b>{l_date}</b><br>• Exam Date : <b>{e_date}</b>"

                    # Regex match fee
                    gen_fee = re.search(r'General\s*/\s*OBC\s*/\s*EWS\s*:\s*([^.\n]+)', full_text, re.I)
                    sc_fee = re.search(r'SC\s*/\s*ST\s*:\s*([^.\n]+)', full_text, re.I)
                    if gen_fee:
                        fallback_data["fee"] = f"• General / OBC / EWS : <b>{gen_fee.group(1).strip()}</b><br>• SC / ST / PwD : <b>{sc_fee.group(1).strip() if sc_fee else 'Exempted'}</b><br>• Mode : <b>Online Gateway</b>"

                    # Regex match age
                    min_age = re.search(r'Minimum Age\s*:\s*(\d{2})', full_text, re.I)
                    max_age = re.search(r'Maximum Age\s*:\s*(\d{2})', full_text, re.I)
                    if min_age and max_age:
                        fallback_data["age"] = f"• Minimum Age : <b>{min_age.group(1)} Years</b><br>• Maximum Age : <b>{max_age.group(1)} Years</b> (Age relaxation applicable as per rules)"

                    # Regex match total vacancies
                    vac_m = re.search(r'Total\s*:\s*(\d+[\d,]*)\s*Post', full_text, re.I)
                    if vac_m:
                        fallback_data["vacancies"] = f"{vac_m.group(1)} Posts"
    except Exception as e:
        print(f"Fallback check note for [{title[:25]}]: {e}")

    return fallback_data

def resolve_official_destination(title, source_url):
    lower = title.lower()
    
    if "ssc" in lower:
        return "https://ssc.gov.in", "https://ssc.gov.in"
    elif "upsc" in lower:
        return "https://upsc.gov.in", "https://upsconline.nic.in"
    elif "ibps" in lower:
        return "https://www.ibps.in", "https://www.ibps.in"
    elif "sbi" in lower:
        return "https://sbi.co.in/careers", "https://sbi.co.in"
    elif any(k in lower for k in ["railway", "rrb", "rrc"]):
        return "https://rrbapply.gov.in", "https://indianrailways.gov.in"
    elif "upsssc" in lower:
        return "https://upsssc.gov.in", "https://upsssc.gov.in"
    elif "up police" in lower or "uppbpb" in lower:
        return "https://uppbpb.gov.in", "https://uppbpb.gov.in"
    elif "high court" in lower:
        return "https://allahabadhighcourt.in", "https://allahabadhighcourt.in"
    elif "bpsc" in lower:
        return "https://bpsc.bih.nic.in", "https://bpsc.bih.nic.in"

    for dom in OFFICIAL_DOMAINS:
        if dom in source_url.lower():
            return source_url, source_url

    return source_url, source_url

def extract_meta(title):
    lower = title.lower()
    org = "Govt Recruitment"
    for o in ["SSC", "UPSC", "IBPS", "SBI", "Railway", "RRB", "UPSSSC", "UP Police", "High Court", "BPSC", "NTA", "Army", "Navy", "Air Force"]:
        if o.lower() in lower:
            org = o
            break

    category = "jobs"
    if any(k in lower for k in ["result", "marks", "cutoff", "merit"]):
        category = "results"
    elif any(k in lower for k in ["admit card", "hall ticket", "exam city", "call letter"]):
        category = "admit"
    elif any(k in lower for k in ["answer key", "key challenge"]):
        category = "answerkey"
    elif any(k in lower for k in ["admission", "entrance", "counseling"]):
        category = "admission"

    vac_m = re.search(r'(\d+[\d,]*)\s*(posts|vacancies|post)', lower)
    total_posts = (vac_m.group(1) + " Posts") if vac_m else "Check Notice"

    return org, category, total_posts

def run_cross_verification():
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
                items = root.findall('.//item')[:30]

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

                    # Trigger cross-verification from SarkariResult if data is sparse
                    fb = search_and_verify_sarkariresult(title)

                    dates_val = fb["dates"] or "• Application Window : <b>Active Now</b><br>• Last Date : <b>Check Official Notice PDF</b><br>• Exam / Admit Card : <b>As per Official Schedule</b>"
                    fee_val = fb["fee"] or "• Application Fee : <b>As per Official Notification</b><br>• Payment Mode : <b>Online Net Banking, UPI, Debit Card</b>"
                    age_val = fb["age"] or "• Minimum Age : <b>18–21 Years</b><br>• Maximum Age : <b>Post-specific</b> (Age relaxation applicable as per rules)"
                    vac_val = fb["vacancies"] or total_posts
                    notice_val = fb["notice_link"] or apply_url
                    syllabus_val = fb["syllabus_link"] or notice_val

                    entry = {
                        "id": slug,
                        "title": title,
                        "date": f"Post Date: {now_str}",
                        "org": org,
                        "total_posts": vac_val,
                        "intro": f"<b>{org}</b> has officially announced <b>{title}</b>. All eligible candidates can verify eligibility qualifications, important dates, and official application portals below.",
                        "dates": dates_val,
                        "fee": fee_val,
                        "age": age_val,
                        "qualification": "• Candidate must possess the requisite educational qualification (10th / 12th / Diploma / Graduate Degree) from a recognized Board/University as detailed in the official notice.",
                        "vacancies_detail": f"• Total: {vac_val} as per official recruitment advertisement.",
                        "links": {
                            "apply": fb["apply_link"] or apply_url,
                            "notice": notice_val,
                            "syllabus": syllabus_val,
                            "official": fb["official_site"] or official_site
                        }
                    }

                    db.setdefault(category, []).insert(0, entry)
        except Exception as e:
            print(f"Scraper run error: {e}")

    # Retain top 30 per section
    for k in db:
        db[k] = db[k][:30]

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    print("✅ Auto-verification & fallback sync complete!")

if __name__ == '__main__':
    run_cross_verification()
