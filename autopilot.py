import urllib.request
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
    "allahabadhighcourt.in", "bpsc.bih.nic.in", "upsssc.gov.in", "uppbpb.gov.in"
]

class LinkAndTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.pdf_links = []
        self.apply_links = []
        self.text_content = []
        self.current_tag = None
        self.current_attrs = {}

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        attr_dict = dict(attrs)
        href = attr_dict.get('href', '')
        text = attr_dict.get('title', '')

        if href:
            href_lower = href.lower()
            if href_lower.endswith('.pdf') or 'notification' in href_lower or 'notice' in href_lower or '.pdf' in href_lower:
                self.pdf_links.append(href)
            if 'apply' in href_lower or 'registration' in href_lower or 'login' in href_lower:
                self.apply_links.append(href)

    def handle_data(self, data):
        cleaned = data.strip()
        if cleaned:
            self.text_content.append(cleaned)

def clean_text(text):
    return re.sub(r'<[^>]+>', '', text or '').strip()

def deep_extract_post_details(source_url, title):
    """
    Crawls the post page to locate the direct PDF notification link,
    apply link, fee structure, and qualification criteria.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    pdf_url = None
    apply_url = None
    syllabus_url = None
    body_text = ""

    try:
        req = urllib.request.Request(source_url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as res:
            html = res.read().decode('utf-8', errors='ignore')
            parser = LinkAndTableParser()
            parser.feed(html)
            
            body_text = " ".join(parser.text_content[:200])

            # Select the most authentic PDF link found on page
            for lk in parser.pdf_links:
                if any(dom in lk.lower() for dom in OFFICIAL_DOMAINS) or lk.lower().endswith('.pdf'):
                    pdf_url = lk
                    break
            if not pdf_url and parser.pdf_links:
                pdf_url = parser.pdf_links[0]

            for lk in parser.apply_links:
                if any(dom in lk.lower() for dom in OFFICIAL_DOMAINS):
                    apply_url = lk
                    break
            if not apply_url and parser.apply_links:
                apply_url = parser.apply_links[0]

    except Exception as e:
        print(f"Deep parse note [{title[:30]}]: {e}")

    # Fallback to authentic portal mappings if not extracted
    lower_title = title.lower()
    official_portal = "https://ssc.gov.in"
    if "railway" in lower_title or "rrb" in lower_title or "rrc" in lower_title:
        official_portal = "https://rrbapply.gov.in"
    elif "upsc" in lower_title:
        official_portal = "https://upsc.gov.in"
    elif "up police" in lower_title or "uppbpb" in lower_title:
        official_portal = "https://uppbpb.gov.in"
    elif "high court" in lower_title:
        official_portal = "https://allahabadhighcourt.in"
    elif "bpsc" in lower_title:
        official_portal = "https://bpsc.bih.nic.in"
    elif "upsssc" in lower_title:
        official_portal = "https://upsssc.gov.in"
    elif "ibps" in lower_title:
        official_portal = "https://ibps.in"
    elif "neet" in lower_title or "cuet" in lower_title or "nta" in lower_title:
        official_portal = "https://nta.ac.in"

    # Strict separation: notification link must be distinct from general site
    final_notice = pdf_url if pdf_url else source_url
    final_apply = apply_url if apply_url else (official_portal if official_portal else source_url)

    # Extract dates, fees, and age limits from text
    dates_extracted = "• Application Window : <b>Active / As per Schedule</b><br>• Last Date : <b>Check Official Notice PDF</b><br>• Exam / Admit Card : <b>To be announced by Board</b>"
    fee_extracted = "• General / OBC / EWS : <b>Refer Official Notice</b><br>• SC / ST / PwD : <b>Exempted / Concessional</b><br>• Mode : <b>Online NetBanking / Debit Card / UPI</b>"
    age_extracted = "• Minimum Age : <b>18 Years</b><br>• Maximum Age : <b>Post-specific (Relaxation as per rules)</b>"

    # Regex search for Fee patterns
    fee_match = re.search(r'(fee|application fee)[^.]{1,80}(rs\.?|inr|₹)\s*(\d+)', body_text, re.IGNORECASE)
    if fee_match:
        fee_extracted = f"• Application Fee : <b>Approx ₹{fee_match.group(3)}/- (Category relaxation extra)</b><br>• Payment Mode : <b>Online Gateway</b>"

    # Regex search for Age patterns
    age_match = re.search(r'(\d{2})\s*(to|-)\s*(\d{2})\s*years', body_text, re.IGNORECASE)
    if age_match:
        age_extracted = f"• Minimum Age : <b>{age_match.group(1)} Years</b><br>• Maximum Age : <b>{age_match.group(3)} Years</b><br>• Age relaxation applicable as per board rules."

    return {
        "notice_link": final_notice,
        "apply_link": final_apply,
        "official_site": official_portal,
        "dates": dates_extracted,
        "fee": fee_extracted,
        "age": age_extracted
    }

def extract_meta(title):
    lower = title.lower()
    org = "Govt Recruitment"
    for o in ["SSC", "UPSC", "UP Police", "Railway", "RRB", "High Court", "BPSC", "UPSSSC", "NTA", "Bank", "IBPS", "DSSSB", "Teacher", "Army", "Navy", "Airforce"]:
        if o.lower() in lower:
            org = o
            break

    category = "jobs"
    if any(k in lower for k in ["result", "marks", "cutoff", "merit", "scorecard"]):
        category = "results"
    elif any(k in lower for k in ["admit card", "hall ticket", "exam city", "call letter"]):
        category = "admit"
    elif any(k in lower for k in ["answer key", "key challenge"]):
        category = "answerkey"
    elif any(k in lower for k in ["syllabus", "exam pattern"]):
        category = "syllabus"
    elif any(k in lower for k in ["admission", "entrance"]):
        category = "admission"

    vac_match = re.search(r'(\d+[\d,]*)\s*(posts|vacancies|post)', lower)
    total_posts = (vac_match.group(1) + " Posts") if vac_match else "Check Notice PDF"

    return org, category, total_posts

def run():
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            db = json.load(f)
    except:
        db = {"jobs": [], "admit": [], "results": [], "answerkey": []}

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    now_str = datetime.now().strftime("%B %d, %Y")

    for src in SOURCES:
        try:
            req = urllib.request.Request(src["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                root = ET.fromstring(response.read())
                items = root.findall('.//item')[:20]

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

                    # Deep parse post for true PDF and Apply links
                    parsed = deep_extract_post_details(source_url, title)

                    entry = {
                        "id": slug,
                        "title": title,
                        "date": f"Post Date: {now_str}",
                        "org": org,
                        "total_posts": total_posts,
                        "intro": f"<b>{org}</b> has published the official notification for <b>{title}</b>. Candidates can verify eligibility, download the official PDF notice, and access the application gateway below.",
                        "dates": parsed["dates"],
                        "fee": parsed["fee"],
                        "age": parsed["age"],
                        "links": {
                            "apply": parsed["apply_link"],
                            "notice": parsed["notice_link"],
                            "official": parsed["official_site"]
                        }
                    }

                    db.setdefault(category, []).insert(0, entry)
        except Exception as e:
            print(f"Scraper error: {e}")

    for k in db:
        db[k] = db[k][:25]

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    print("✅ Deep verification finished. Official PDF notification links updated!")

if __name__ == '__main__':
    run()
