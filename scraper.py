import re
import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"
}

CONTENT_SELECTORS = [
    {"tag": "article", "class_pattern": "blog-post__article"},
    {"tag": "article", "class_pattern": "post-content"},
    {"tag": "article", "class_pattern": "article-body"},
    {"tag": "article", "class_pattern": "entry-content"},
    {"tag": "div",     "class_pattern": "post-content"},
    {"tag": "div",     "class_pattern": "entry-content"},
    {"tag": "div",     "class_pattern": "article-content"},
    {"tag": "div",     "class_pattern": "article-body"},
    {"tag": "div",     "class_pattern": "blog-content"},
    {"tag": "div",     "class_pattern": "content-body"},
    {"tag": "main",    "class_pattern": None},
    {"tag": "article", "class_pattern": None},
]

def find_content_area(soup):
    for sel in CONTENT_SELECTORS:
        if sel["class_pattern"]:
            el = soup.find(sel["tag"], class_=re.compile(sel["class_pattern"], re.I))
        else:
            el = soup.find(sel["tag"])
        if el:
            return el
    return soup.find("body") or soup

def extract_title(soup):
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    title = soup.find("title")
    return title.get_text(strip=True) if title else ""

def extract_meta_description(soup):
    meta = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    if meta and meta.get("content"):
        return meta["content"].strip()
    return ""

def extract_heading_tree(area) -> list[dict]:
    """
    Extract H2/H3 hierarchy as a structured tree.
    Returns list of {"h2": "...", "h3s": ["...", "..."]}
    """
    tree = []
    current_h2 = None

    for tag in area.find_all(["h2", "h3"]):
        text = tag.get_text(strip=True)
        if not text:
            continue
        if tag.name == "h2":
            current_h2 = {"h2": text, "h3s": []}
            tree.append(current_h2)
        elif tag.name == "h3" and current_h2 is not None:
            current_h2["h3s"].append(text)

    return tree

def extract_faq_schema(soup) -> list[dict]:
    """
    Try to extract FAQ items from JSON-LD schema or FAQ itemtype markup.
    Returns list of {"question": "...", "answer": "..."}
    """
    faqs = []

    # JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            import json
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = next((d for d in data if d.get("@type") == "FAQPage"), None)
            if data and data.get("@type") == "FAQPage":
                for item in data.get("mainEntity", []):
                    q = item.get("name", "")
                    a_block = item.get("acceptedAnswer", {})
                    a = a_block.get("text", "") if isinstance(a_block, dict) else ""
                    if q:
                        faqs.append({"question": q, "answer": a[:300]})
        except Exception:
            continue

    # Microdata fallback
    if not faqs:
        faq_items = soup.find_all(attrs={"itemtype": re.compile("Question", re.I)})
        for item in faq_items:
            q_el = item.find(attrs={"itemprop": "name"})
            a_el = item.find(attrs={"itemprop": "text"})
            q = q_el.get_text(strip=True) if q_el else ""
            a = a_el.get_text(strip=True)[:300] if a_el else ""
            if q:
                faqs.append({"question": q, "answer": a})

    return faqs[:8]

def extract_body(area):
    for tag in area(["script", "style", "pre", "figure", "nav", "footer", "aside", "form"]):
        tag.decompose()

    lines = []
    for el in area.find_all(["h2", "h3", "p", "li"]):
        text = el.get_text(strip=True)
        if not text:
            continue
        if el.name == "h2":
            lines.append(f"\n## {text}")
        elif el.name == "h3":
            lines.append(f"\n### {text}")
        elif el.name == "li":
            lines.append(f"- {text}")
        elif el.name == "p":
            lines.append(f"\n{text}")

    body = "\n".join(lines)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body[:40000]

def count_words(text):
    return len(text.split())

def scrape_with_httpx(url):
    r = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
    r.raise_for_status()
    return r.text

def scrape_with_playwright(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        html = page.content()
        browser.close()
        return html

def parse_html(html):
    soup = BeautifulSoup(html, "html.parser")
    area = find_content_area(soup)
    return {
        "title":        extract_title(soup),
        "meta":         extract_meta_description(soup),
        "heading_tree": extract_heading_tree(area),
        "faq_schema":   extract_faq_schema(soup),
        "body":         extract_body(area),
    }

def scrape_url(url: str) -> dict:
    try:
        html = scrape_with_httpx(url)
        parsed = parse_html(html)
        word_count = count_words(parsed["body"])

        if word_count < 100:
            html = scrape_with_playwright(url)
            parsed = parse_html(html)
            word_count = count_words(parsed["body"])

        if parsed["title"].lower() in ["access denied", "403 forbidden", "just a moment..."]:
            return {
                "url":          url,
                "success":      False,
                "title":        "",
                "meta":         "",
                "heading_tree": [],
                "faq_schema":   [],
                "body":         "",
                "word_count":   0,
                "error":        "Blocked by site (access denied)"
            }

        return {
            "url":          url,
            "success":      True,
            "title":        parsed["title"],
            "meta":         parsed["meta"],
            "heading_tree": parsed["heading_tree"],
            "faq_schema":   parsed["faq_schema"],
            "body":         parsed["body"],
            "word_count":   word_count,
            "error":        None
        }

    except Exception as e:
        return {
            "url":          url,
            "success":      False,
            "title":        "",
            "meta":         "",
            "heading_tree": [],
            "faq_schema":   [],
            "body":         "",
            "word_count":   0,
            "error":        str(e)
        }

def scrape_urls(urls: list[str]) -> list[dict]:
    return [scrape_url(url) for url in urls]
