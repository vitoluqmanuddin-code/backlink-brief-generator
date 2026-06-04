import re
import httpx
import gspread
from google.oauth2.service_account import Credentials
from bs4 import BeautifulSoup
from scraper import scrape_url
from brief import generate_brief
from openai import OpenAI
from typing import cast
from openai.types.chat import ChatCompletionMessageParam
import streamlit as st


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

MEDIA_ANALYSIS_PROMPT = """Kamu adalah analis media digital Indonesia. Berdasarkan artikel-artikel sample dari media ini, analisis:

1. Profil audiens utama (siapa pembaca media ini)
2. Tone penulisan (formal/informal, teknis/umum, dll)
3. Topik-topik utama yang dibahas
4. Level kedalaman konten (permukaan/menengah/mendalam)
5. Gaya penyajian (narasi/listicle/data-driven/dll)

Output dalam format JSON:
{
  "audiens": "deskripsi singkat audiens utama",
  "tone": "deskripsi tone penulisan",
  "topik_utama": ["topik1", "topik2", "topik3"],
  "kedalaman": "permukaan/menengah/mendalam",
  "gaya": "deskripsi gaya penyajian",
  "konteks_brief": "1-2 kalimat panduan untuk menulis konten yang sesuai dengan media ini"
}

Jawab HANYA dengan JSON, tanpa preamble atau markdown backticks."""


def get_gsheet_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES,
    )
    return gspread.authorize(creds)


def fetch_all_profiles() -> dict:
    """Fetch semua profil media dari Google Sheet."""
    try:
        client = get_gsheet_client()
        sheet  = client.open_by_key(st.secrets["SHEET_ID"]).sheet1
        rows   = sheet.get_all_records()
        return {row["Domain"]: row for row in rows if row.get("Domain")}
    except Exception as e:
        st.warning(f"Gagal fetch profil media dari Sheet: {e}")
        return {}


def save_profile_to_sheet(domain: str, profile: dict):
    """Tulis profil media baru ke Google Sheet."""
    try:
        client = get_gsheet_client()
        sheet  = client.open_by_key(st.secrets["SHEET_ID"]).sheet1
        from datetime import date
        sheet.append_row([
            domain,
            profile.get("nama", ""),
            profile.get("audiens", ""),
            profile.get("tone", ""),
            ", ".join(profile.get("topik_utama", [])),
            profile.get("kedalaman", ""),
            profile.get("gaya", ""),
            profile.get("konteks_brief", ""),
            str(date.today()),
        ])
    except Exception as e:
        st.warning(f"Gagal simpan profil ke Sheet: {e}")


def extract_domain(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url.startswith("http"):
        url = "https://" + url
    match = re.match(r"https?://([^/]+)", url)
    return match.group(1) if match else url


def fetch_sitemap_urls(base_url: str, max_urls: int = 20) -> list[str]:
    """Coba fetch sitemap dan ambil URL artikel terbaru."""
    base_url = base_url.strip().rstrip("/")
    if not base_url.startswith("http"):
        base_url = "https://" + base_url

    sitemap_candidates = []

    # Cek robots.txt dulu
    try:
        r = httpx.get(f"{base_url}/robots.txt", timeout=10, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"})
        for line in r.text.splitlines():
            if line.lower().startswith("sitemap:"):
                sitemap_candidates.append(line.split(":", 1)[1].strip())
    except Exception:
        pass

    # Fallback sitemap URLs
    if not sitemap_candidates:
        sitemap_candidates = [
            f"{base_url}/sitemap.xml",
            f"{base_url}/sitemap_index.xml",
            f"{base_url}/sitemap-index.xml",
            f"{base_url}/news-sitemap.xml",
        ]

    urls = []
    for sitemap_url in sitemap_candidates[:3]:
        try:
            r = httpx.get(sitemap_url, timeout=10, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"})
            soup = BeautifulSoup(r.text, "xml")
            locs = soup.find_all("loc")
            for loc in locs:
                u = loc.get_text(strip=True)
                if u and base_url in u and u not in urls:
                    urls.append(u)
            if urls:
                break
        except Exception:
            continue

    # Ambil yang terbaru, skip homepage dan kategori
    article_urls = [
        u for u in urls
        if len(u.split("/")) > 4
        and not u.endswith(".xml")
    ]

    return article_urls[:max_urls]


def analyze_media(
    media_url: str,
    api_key: str,
    model_id: str,
) -> dict:
    """
    Analisis profil audiens media dari sitemap + scraping artikel sample.
    Return dict profil media.
    """
    domain   = extract_domain(media_url)
    base_url = f"https://{domain}"

    # Fetch sitemap URLs
    with st.spinner(f"Fetching sitemap {domain}..."):
        sitemap_urls = fetch_sitemap_urls(base_url)

    if not sitemap_urls:
        st.warning(f"Sitemap tidak ditemukan untuk {domain}. Coba scrape homepage.")
        sitemap_urls = [base_url]

    # Scrape 4 artikel sample
    sample_urls = sitemap_urls[:4]
    with st.spinner(f"Scraping {len(sample_urls)} artikel sample dari {domain}..."):
        samples = [scrape_url(u) for u in sample_urls]

    valid_samples = [s for s in samples if s["success"] and s["word_count"] >= 100]

    if not valid_samples:
        raise RuntimeError(f"Tidak ada artikel yang berhasil di-scrape dari {domain}.")

    # Susun konten sample untuk Claude
    sample_text = ""
    for i, s in enumerate(valid_samples, 1):
        sample_text += f"\n--- Artikel {i}: {s['url']} ---\n"
        sample_text += f"Title: {s['title']}\n"
        if s.get("heading_tree"):
            for node in s["heading_tree"][:5]:
                sample_text += f"H2: {node['h2']}\n"
        sample_text += f"Body (500 char): {s['body'][:500]}\n"

    # Analisis via Claude/GPT
    from config import get_client
    client = get_client(api_key)

    messages = cast(list[ChatCompletionMessageParam], [
        {"role": "system", "content": MEDIA_ANALYSIS_PROMPT},
        {"role": "user", "content": f"Domain: {domain}\n\nSample artikel:\n{sample_text}"},
    ])

    if "gpt" in model_id.lower():
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_completion_tokens=1000,
            temperature=0.1,
        )
    else:
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=1000,
            temperature=0.1,
        )

    raw = (response.choices[0].message.content or "").strip()

    import json
    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        profile = json.loads(clean)
    except Exception:
        profile = {"konteks_brief": raw}

    profile["nama"] = domain
    return profile