import streamlit as st
import subprocess
import sys

# Install playwright browsers if not already installed
try:
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"],
                   capture_output=True, timeout=60)
except Exception:
    pass

from serp import fetch_serp
from scraper import scrape_urls
from brief import detect_format, generate_brief
from config import MODELS, DEFAULT_MODEL, FORMATS, PRODUCTS, calculate_cost
from media_analyzer import analyze_media, fetch_all_profiles, extract_domain
from boilerplate import fetch_boilerplate_all, get_product_list, get_module_list, get_feature_list, build_boilerplate_text, save_boilerplate

st.set_page_config(page_title="Backlink Brief Generator", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("Backlink Brief Generator")
    with st.form("login_form"):
        pwd = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if pwd == st.secrets["APP_PASSWORD"]:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Password salah.")
    st.stop()
st.title("Backlink Brief Generator")
st.caption("Mekari Backlink Article Brief — by M. Vito Luqmanuddin")

# ── SESSION STATE ─────────────────────────────────────────────────────────────
for key, default in {
    "serp_cache":      {},
    "serp_result":     None,
    "scraped":         None,
    "scraped_preview": None,
    "brief_result":    None,
    "usage":           None,
    "model_id":        DEFAULT_MODEL,
    "media_profiles":        {},
    "media_profile_preview": None,
    "boilerplate_data":      None,
    "boilerplate_text":      "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── LOAD MEDIA PROFILES FROM SHEET ───────────────────────────────────────────
if not st.session_state["media_profiles"]:
    st.session_state["media_profiles"] = fetch_all_profiles()

# ── LOAD BOILERPLATE FROM SHEET ──────────────────────────────────────────────
if not st.session_state["boilerplate_data"]:
    st.session_state["boilerplate_data"] = fetch_boilerplate_all()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("API Keys")
    api_key  = st.text_input("Dinoiki API Key", type="password")
    serp_key = st.text_input("SerpApi Key", type="password",
                              help="Wajib untuk mode Auto")
    st.divider()

    st.header("Model")
    model    = st.selectbox("Pilih model", list(MODELS.keys()), index=0)
    model_id = MODELS[model]
    st.divider()

    st.header("Mode input URL")
    url_mode = st.radio(
        "Sumber URL kompetitor:",
        ["Auto — scrape semua", "Auto — pilih dari SERP", "Manual"],
        index=0,
    )
    st.divider()

    if st.button("Clear cache"):
        st.session_state["serp_cache"]       = {}
        st.session_state["serp_result"]      = None
        st.session_state["scraped"]          = None
        st.session_state["brief_result"]     = None
        st.session_state["usage"]            = None
        st.session_state["boilerplate_data"] = None
        st.session_state["media_profiles"]   = {}
        st.success("Cache dikosongkan.")


# ── MAIN FORM ─────────────────────────────────────────────────────────────────
st.subheader("Brief Inputs")

col1, col2 = st.columns(2)

with col1:
    keyword      = st.text_input("Keyword *", placeholder="e.g. spend management software")
    product      = st.selectbox("Produk Mekari *", PRODUCTS)
    target_media = st.text_input("URL Placement media *", placeholder="e.g. https://katadata.co.id")
    mekari_source = st.text_area(
        "Mekari source (opsional)",
        placeholder="Paste URL atau teks deskripsi produk Mekari. Kosongkan jika tidak ada.",
        height=100,
    )

with col2:
    url1    = st.text_input("URL Backlink 1 *", placeholder="https://expense.mekari.com/...")
    anchor1 = st.text_input("Anchor Text 1 *", placeholder="e.g. software manajemen pengeluaran")
    url2    = st.text_input("URL Backlink 2 *", placeholder="https://expense.mekari.com/...")
    anchor2 = st.text_input("Anchor Text 2 *", placeholder="e.g. Mekari Expense")

st.divider()

col3, col4 = st.columns(2)

with col3:
    format_choice = st.selectbox(
        "Format artikel",
        list(FORMATS.keys()),
        format_func=lambda k: FORMATS[k],
        index=0,
    )

with col4:
    n_tools = None
    if format_choice == "listicle":
        n_tools = st.number_input("Jumlah tools dalam listicle", min_value=3, max_value=15, value=7)

# ── BOILERPLATE PRODUK ────────────────────────────────────────────────────────
st.divider()
with st.expander("Boilerplate produk Mekari (opsional)", expanded=False):
    bp_data = st.session_state["boilerplate_data"] or {"products": [], "modules": [], "features": []}
    product_list = get_product_list(bp_data)

    if not product_list:
        st.info("Belum ada boilerplate. Tambahkan via form di bawah atau langsung di Google Sheet.")
    else:
        # Produk otomatis dari main form
        bp_product = product

        col_bp1, col_bp2 = st.columns(2)
        with col_bp1:
            bp_module_list = get_module_list(bp_data, bp_product)
            bp_module = st.selectbox("Modul (opsional)", ["(semua)"] + bp_module_list, key="bp_module")
        with col_bp2:
            bp_feature_list = get_feature_list(bp_data, bp_product, bp_module) if bp_module != "(semua)" else []
            bp_feature = st.selectbox("Fitur (opsional)", ["(semua)"] + bp_feature_list, key="bp_feature")

        selected_module  = None if bp_module == "(semua)" else bp_module
        selected_feature = None if bp_feature == "(semua)" else bp_feature
        bp_text = build_boilerplate_text(bp_data, bp_product, selected_module, selected_feature)
        st.session_state["boilerplate_text"] = bp_text
        if bp_text:
            st.markdown(f"**Preview boilerplate — {bp_product}:**")
            st.text_area("", value=bp_text, height=150, disabled=True)
        else:
            st.info(f"Belum ada boilerplate untuk {bp_product}. Tambahkan via form di bawah atau langsung di Google Sheet.")

    st.divider()
    st.markdown("**Tambah boilerplate baru**")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        new_level   = st.selectbox("Level", ["Produk", "Modul", "Fitur"], key="new_level")
        st.text_input("Produk", value=product, disabled=True, key="new_product_display")
        new_product = product
        new_module  = st.text_input("Modul *", key="new_module") if new_level in ["Modul", "Fitur"] else ""
        new_feature = st.text_input("Fitur *", key="new_feature") if new_level == "Fitur" else ""
    with col_f2:
        new_brief = st.text_area("Brief / boilerplate", height=150, key="new_brief")

    if st.button("Simpan boilerplate", key="save_bp"):
        errors = []
        if not new_brief:
            errors.append("Brief wajib diisi.")
        if new_level == "Modul" and not new_module:
            errors.append("Nama modul wajib diisi.")
        if new_level == "Fitur" and not new_module:
            errors.append("Nama modul wajib diisi.")
        if new_level == "Fitur" and not new_feature:
            errors.append("Nama fitur wajib diisi.")
        if errors:
            for e in errors:
                st.error(e)
        else:
            save_boilerplate(new_level, new_product, new_module, new_feature, new_brief)
            st.success("Boilerplate tersimpan.")
            st.session_state["boilerplate_data"] = fetch_boilerplate_all()

# Manual URL input
if url_mode == "Manual":
    st.divider()
    st.markdown("**URL Kompetitor (manual)**")
    url_input  = st.text_area(
        "Masukkan URL kompetitor, satu per baris (minimal 3)",
        height=130,
        placeholder="https://...\nhttps://...\nhttps://..."
    )
    manual_urls = [u.strip() for u in url_input.splitlines() if u.strip()]
else:
    manual_urls = []


# ── VALIDASI INPUT DASAR ──────────────────────────────────────────────────────
def validate_inputs(check_serp=False, check_manual=False):
    errors = []
    if not api_key:
        errors.append("Dinoiki API Key belum diisi.")
    if not keyword:
        errors.append("Keyword belum diisi.")
    if not url1 or not anchor1:
        errors.append("URL dan Anchor Text 1 wajib diisi.")
    if not url2 or not anchor2:
        errors.append("URL dan Anchor Text 2 wajib diisi.")
    if check_serp and not serp_key:
        errors.append("SerpApi Key wajib diisi untuk mode Auto.")
    if check_manual and len(manual_urls) < 3:
        errors.append("Minimal 3 URL kompetitor untuk mode Manual.")
    return errors

def get_or_analyze_media(media_url: str) -> dict | None:
    """Ambil profil media dari cache/Sheet, atau analisis baru."""
    if not media_url:
        return None
    domain = extract_domain(media_url)
    
    # Cek session cache
    if domain in st.session_state["media_profiles"]:
        st.info(f"Profil media {domain} diambil dari cache.")
        return st.session_state["media_profiles"][domain]
    
    # Analisis baru
    try:
        st.info(f"Menganalisis profil media {domain}...")
        profile = analyze_media(media_url, api_key, model_id)
        st.session_state["media_profiles"][domain] = profile
        from media_analyzer import save_profile_to_sheet
        save_profile_to_sheet(domain, profile)
        return profile
    except Exception as e:
        st.warning(f"Gagal analisis media: {e}")
        st.exception(e)
        return None


def show_media_profile(profile: dict):
    """Tampilkan profil media di UI."""
    with st.expander(f"Profil media — {profile.get('nama', '')}", expanded=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Audiens:** {profile.get('audiens', '-')}")
            st.markdown(f"**Tone:** {profile.get('tone', '-')}")
            st.markdown(f"**Kedalaman:** {profile.get('kedalaman', '-')}")
        with col_b:
            st.markdown(f"**Gaya:** {profile.get('gaya', '-')}")
            topik = profile.get('topik_utama', [])
            if topik:
                st.markdown(f"**Topik utama:** {', '.join(topik)}")
        if profile.get('konteks_brief'):
            st.info(f"💡 {profile['konteks_brief']}")


# ── MODE: AUTO — SCRAPE SEMUA ─────────────────────────────────────────────────
if url_mode == "Auto — scrape semua":
    st.divider()
    if st.button("Generate Brief", type="primary", use_container_width=True):
        errors = validate_inputs(check_serp=True)
        for e in errors:
            st.error(e)
        if errors:
            st.stop()

        # Fetch SERP
        cache_key = keyword.strip().lower()
        if cache_key in st.session_state["serp_cache"]:
            st.info("Menggunakan SERP cache.")
            cached   = st.session_state["serp_cache"][cache_key]
            serp_data = cached["serp"]
            scraped  = cached["scraped"]
        else:
            with st.spinner("Fetching SERP..."):
                try:
                    serp_data = fetch_serp(keyword, api_key=serp_key)
                except Exception as e:
                    st.error(f"SERP error: {e}")
                    st.stop()

            urls = [r["url"] for r in serp_data["organic"]]
            st.success(f"{len(urls)} URL diambil dari SERP.")

            with st.expander("URL yang di-scrape"):
                for r in serp_data["organic"]:
                    st.write(f"{r['position']}. [{r['title']}]({r['url']})")

            with st.spinner("Scraping kompetitor..."):
                scraped = scrape_urls(urls)

            st.session_state["serp_cache"][cache_key] = {"serp": serp_data, "scraped": scraped}

        ok = sum(1 for r in scraped if r["success"] and r["word_count"] >= 100)
        st.success(f"{ok}/{len(scraped)} URL berhasil di-scrape.")
        with st.expander("Detail scraping"):
            for r in scraped:
                status = f"✅ {r['word_count']} words" if r["success"] and r["word_count"] >= 100 else f"❌ {r.get('error', 'Empty')}"
                h2s  = f" | {len(r.get('heading_tree', []))} H2s" if r.get("heading_tree") else ""
                faqs = f" | {len(r.get('faq_schema', []))} FAQ" if r.get("faq_schema") else ""
                st.write(f"{status}{h2s}{faqs} — {r['url']}")

        if ok < 2:
            st.error("Terlalu sedikit sumber valid (minimal 2).")
            st.stop()

        # Analisis media
        media_profile = get_or_analyze_media(target_media)
        if media_profile:
            show_media_profile(media_profile)

        # Detect format
        article_format = format_choice
        if format_choice == "auto":
            with st.spinner("Mendeteksi format artikel..."):
                article_format = detect_format(
                    serp_data=serp_data,
                    keyword=keyword,
                    api_key=api_key,
                    model=model_id,
                )
            st.info(f"Format terdeteksi: **{article_format}**")

        # Generate
        with st.spinner("Generating brief..."):
            try:
                result, usage = generate_brief(
                    keyword=keyword,
                    product=product,
                    url1=url1,
                    anchor1=anchor1,
                    url2=url2,
                    anchor2=anchor2,
                    target_media=target_media,
                    article_format=article_format,
                    mekari_source=mekari_source,
                    n_tools=int(n_tools) if n_tools else None,
                    scraped_results=scraped,
                    serp_data=serp_data,
                    api_key=api_key,
                    model=model_id,
                    media_profile=media_profile,
                    boilerplate_text=st.session_state.get("boilerplate_text", ""),
                )
                st.session_state["brief_result"] = result
                st.session_state["usage"]        = usage
                st.session_state["model_id"]     = model_id
            except Exception as e:
                st.error(f"Generate error: {e}")
                st.stop()


# ── MODE: AUTO — PILIH DARI SERP
elif url_mode == "Auto — pilih dari SERP":
    st.divider()

    # Step 1: Fetch SERP
    if st.button("Fetch SERP", use_container_width=True):
        errors = validate_inputs(check_serp=True)
        for e in errors:
            st.error(e)
        if errors:
            st.stop()

        cache_key = keyword.strip().lower()
        if cache_key in st.session_state["serp_cache"]:
            st.info("Menggunakan SERP cache.")
            st.session_state["serp_result"] = st.session_state["serp_cache"][cache_key]["serp"]
        else:
            with st.spinner("Fetching SERP..."):
                try:
                    serp_data = fetch_serp(keyword, api_key=serp_key)
                    st.session_state["serp_result"] = serp_data
                except Exception as e:
                    st.error(f"SERP error: {e}")
                    st.stop()

    # Step 2: Pilih URL
    if st.session_state["serp_result"]:
        serp_data = st.session_state["serp_result"]
        all_urls  = [r["url"] for r in serp_data["organic"]]

        with st.expander("Semua hasil SERP", expanded=True):
            for r in serp_data["organic"]:
                st.write(f"{r['position']}. [{r['title']}]({r['url']})")
            paa = serp_data.get("people_also_ask", [])
            if paa:
                st.markdown("**People Also Ask:**")
                for p in paa:
                    st.write(f"• {p['question']}")

        selected_urls = st.multiselect(
            "Pilih 3-5 URL yang akan di-scrape:",
            options=all_urls,
            default=all_urls[:5],
            format_func=lambda u: next(
                (f"{r['position']}. {r['title']}" for r in serp_data["organic"] if r["url"] == u),
                u
            ),
        )

        if len(selected_urls) < 3:
            st.warning("Pilih minimal 3 URL.")
        else:
            # Step 3: Scrape
            if st.button("Scrape URL", use_container_width=True):
                with st.spinner("Scraping URL yang dipilih..."):
                    st.session_state["scraped_preview"] = scrape_urls(selected_urls)
                    st.session_state["brief_result"]    = None
                st.session_state["media_profile_preview"] = get_or_analyze_media(target_media)

            # Preview hasil scraping
            if st.session_state["media_profile_preview"]:
                show_media_profile(st.session_state["media_profile_preview"])

            if st.session_state["scraped_preview"]:
                scraped = st.session_state["scraped_preview"]
                ok = sum(1 for r in scraped if r["success"] and r["word_count"] >= 100)
                st.success(f"{ok}/{len(scraped)} URL berhasil di-scrape.")

                for r in scraped:
                    status = f"✅ {r['word_count']} words" if r["success"] and r["word_count"] >= 100 else f"❌ {r.get('error', 'Empty')}"
                    h2s    = f" | {len(r.get('heading_tree', []))} H2s" if r.get("heading_tree") else ""
                    faqs   = f" | {len(r.get('faq_schema', []))} FAQ" if r.get("faq_schema") else ""
                    body   = r.get("body", "")
                    est_tokens = len(body) // 4
                    with st.expander(f"{status}{h2s}{faqs} — {r['url']}"):
                        tab1, tab2 = st.tabs(["Struktur", "Full Body"])
                        with tab1:
                            if r.get("heading_tree"):
                                st.markdown("**Heading structure:**")
                                for node in r["heading_tree"]:
                                    st.write(f"H2: {node['h2']}")
                                    for h3 in node.get("h3s", []):
                                        st.write(f"　H3: {h3}")
                            if r.get("faq_schema"):
                                st.markdown("**FAQ schema:**")
                                for f in r["faq_schema"]:
                                    st.write(f"Q: {f['question']}")
                            if r.get("meta"):
                                st.markdown("**Meta description:**")
                                st.write(r["meta"])
                        with tab2:
                            st.caption(f"Panjang body: {len(body):,} karakter | Est. token: ~{est_tokens:,}")
                            st.text_area(
                                label="Full body",
                                value=body,
                                height=400,
                                key=f"body_{r['url']}",
                            )

                if ok < 2:
                    st.error("Terlalu sedikit sumber valid (minimal 2).")
                else:
                    # Step 4: Generate Brief
                    if st.button("Generate Brief", type="primary", use_container_width=True):
                        errors = validate_inputs()
                        for e in errors:
                            st.error(e)
                        if errors:
                            st.stop()

                        media_profile = st.session_state.get("media_profile_preview")

                        article_format = format_choice
                        if format_choice == "auto":
                            with st.spinner("Mendeteksi format artikel..."):
                                article_format = detect_format(
                                    serp_data=serp_data,
                                    keyword=keyword,
                                    api_key=api_key,
                                    model=model_id,
                                )
                            st.info(f"Format terdeteksi: **{article_format}**")

                        with st.spinner("Generating brief..."):
                            try:
                                result, usage = generate_brief(
                                    keyword=keyword,
                                    product=product,
                                    url1=url1,
                                    anchor1=anchor1,
                                    url2=url2,
                                    anchor2=anchor2,
                                    target_media=target_media,
                                    article_format=article_format,
                                    mekari_source=mekari_source,
                                    n_tools=int(n_tools) if n_tools else None,
                                    scraped_results=scraped,
                                    serp_data=serp_data,
                                    api_key=api_key,
                                    model=model_id,
                                    media_profile=media_profile,
                                    boilerplate_text=st.session_state.get("boilerplate_text", ""),
                                )
                                st.session_state["brief_result"] = result
                                st.session_state["usage"]        = usage
                                st.session_state["model_id"]     = model_id
                            except Exception as e:
                                st.error(f"Generate error: {e}")
                                st.stop()


# ── MODE: MANUAL ──────────────────────────────────────────────────────────────
elif url_mode == "Manual":
    st.divider()
    if st.button("Generate Brief", type="primary", use_container_width=True):
        errors = validate_inputs(check_manual=True)
        for e in errors:
            st.error(e)
        if errors:
            st.stop()

        with st.spinner("Scraping URL manual..."):
            scraped = scrape_urls(manual_urls)

        ok = sum(1 for r in scraped if r["success"] and r["word_count"] >= 100)
        st.success(f"{ok}/{len(scraped)} URL berhasil di-scrape.")
        with st.expander("Detail scraping"):
            for r in scraped:
                status = f"✅ {r['word_count']} words" if r["success"] and r["word_count"] >= 100 else f"❌ {r.get('error', 'Empty')}"
                h2s  = f" | {len(r.get('heading_tree', []))} H2s" if r.get("heading_tree") else ""
                faqs = f" | {len(r.get('faq_schema', []))} FAQ" if r.get("faq_schema") else ""
                st.write(f"{status}{h2s}{faqs} — {r['url']}")

        if ok < 2:
            st.error("Terlalu sedikit sumber valid (minimal 2).")
            st.stop()

        media_profile = get_or_analyze_media(target_media)
        if media_profile:
            show_media_profile(media_profile)

        article_format = format_choice
        with st.spinner("Generating brief..."):
            try:
                result, usage = generate_brief(
                    keyword=keyword,
                    product=product,
                    url1=url1,
                    anchor1=anchor1,
                    url2=url2,
                    anchor2=anchor2,
                    target_media=target_media,
                    article_format=article_format,
                    mekari_source=mekari_source,
                    n_tools=int(n_tools) if n_tools else None,
                    scraped_results=scraped,
                    serp_data=None,
                    api_key=api_key,
                    model=model_id,
                    media_profile=media_profile,
                    boilerplate_text=st.session_state.get("boilerplate_text", ""),
                )
                st.session_state["brief_result"] = result
                st.session_state["usage"]        = usage
                st.session_state["model_id"]     = model_id
            except Exception as e:
                st.error(f"Generate error: {e}")
                st.stop()


# ── OUTPUT
if st.session_state["brief_result"]:
    st.divider()
    if st.session_state.get("usage"):
        u    = st.session_state["usage"]
        cost = calculate_cost(
            st.session_state.get("model_id", ""),
            u.prompt_tokens,
            u.completion_tokens,
        )
        st.caption(
            f"Token usage — prompt: {u.prompt_tokens} | "
            f"completion: {u.completion_tokens} | "
            f"total: {u.total_tokens} | "
            f"est. cost: ${cost:.4f}"
        )
    st.subheader("Brief Output")
    st.text_area(
        label="Brief (copy dari sini)",
        value=st.session_state["brief_result"],
        height=600,
    )
    st.download_button(
        label="Download .md",
        data=st.session_state["brief_result"],
        file_name=f"brief-{keyword.replace(' ', '-') if keyword else 'output'}.md",
        mime="text/markdown",
    )