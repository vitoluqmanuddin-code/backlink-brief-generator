import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_gsheet_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES,
    )
    return gspread.authorize(creds)


def fetch_boilerplate_all() -> dict:
    """
    Fetch semua boilerplate dari 3 tab: Products, Modules, Features.
    Return dict:
    {
        "products": [{"Product": ..., "Brief": ...}, ...],
        "modules":  [{"Product": ..., "Module": ..., "Brief": ...}, ...],
        "features": [{"Product": ..., "Module": ..., "Feature": ..., "Brief": ...}, ...],
    }
    """
    try:
        client    = get_gsheet_client()
        workbook  = client.open_by_key(st.secrets["SHEET_ID"])
        products  = workbook.worksheet("Products").get_all_records()
        modules   = workbook.worksheet("Modules").get_all_records()
        features  = workbook.worksheet("Features").get_all_records()
        return {
            "products": products,
            "modules":  modules,
            "features": features,
        }
    except Exception as e:
        st.warning(f"Gagal fetch boilerplate dari Sheet: {e}")
        return {"products": [], "modules": [], "features": []}


def get_product_list(data: dict) -> list[str]:
    products = {r["Product"] for r in data["products"] if r.get("Product")}
    from_modules = {r["Product"] for r in data["modules"] if r.get("Product")}
    from_features = {r["Product"] for r in data["features"] if r.get("Product")}
    all_products = products | from_modules | from_features
    return sorted(all_products)


def get_module_list(data: dict, product: str) -> list[str]:
    modules = {
        r["Module"] for r in data["modules"]
        if r.get("Product") == product and r.get("Module")
    }
    from_features = {
        r["Module"] for r in data["features"]
        if r.get("Product") == product and r.get("Module")
    }
    return sorted(modules | from_features)


def get_feature_list(data: dict, product: str, module: str) -> list[str]:
    return sorted([
        r["Feature"] for r in data["features"]
        if r.get("Product") == product
        and r.get("Module") == module
        and r.get("Feature")
    ])


def build_boilerplate_text(data: dict, product: str, module: str | None, feature: str | None) -> str:
    """
    Gabungkan boilerplate sesuai pilihan user.
    - Produk saja → semua boilerplate produk + modul + fitur untuk produk itu
    - Produk + Modul → boilerplate modul + semua fitur di modul itu
    - Produk + Modul + Fitur → hanya boilerplate fitur itu
    """
    parts = []

    # Produk selalu masuk
    for r in data["products"]:
        if r.get("Product") == product and r.get("Brief"):
            parts.append(f"[Produk: {product}]\n{r['Brief']}")

    st.write(f"DEBUG build: module={module!r}, feature={feature!r}, parts before feature block={parts}")
    if feature and module:
        # Pilih fitur → produk + fitur saja
        st.write(f"DEBUG masuk blok feature+module")
        for r in data["features"]:
            if r.get("Product") == product and r.get("Module") == module and r.get("Feature") == feature:
                if r.get("Brief"):
                    st.write(f"DEBUG append fitur: {feature}")
                    parts.append(f"[Fitur: {feature}]\n{r['Brief']}")

    elif module and not feature:
        # Pilih modul → produk + modul + semua fitur di modul
        for r in data["modules"]:
            if r.get("Product") == product and r.get("Module") == module:
                if r.get("Brief"):
                    parts.append(f"[Modul: {module}]\n{r['Brief']}")
        for r in data["features"]:
            if r.get("Product") == product and r.get("Module") == module:
                if r.get("Brief"):
                    parts.append(f"[Fitur: {r['Feature']}]\n{r['Brief']}")

    else:
        # Pilih produk saja → semua modul + semua fitur
        for r in data["modules"]:
            if r.get("Product") == product and r.get("Brief"):
                parts.append(f"[Modul: {r['Module']}]\n{r['Brief']}")
        for r in data["features"]:
            if r.get("Product") == product and r.get("Brief"):
                parts.append(f"[Fitur: {r['Feature']}]\n{r['Brief']}")

    return "\n\n".join(parts)


def save_boilerplate(level: str, product: str, module: str, feature: str, brief: str):
    """Simpan boilerplate baru ke Sheet."""
    try:
        client   = get_gsheet_client()
        workbook = client.open_by_key(st.secrets["SHEET_ID"])

        if level == "Produk":
            sheet = workbook.worksheet("Products")
            sheet.append_row([product, brief])
        elif level == "Modul":
            sheet = workbook.worksheet("Modules")
            sheet.append_row([product, module, brief])
        elif level == "Fitur":
            sheet = workbook.worksheet("Features")
            sheet.append_row([product, module, feature, brief])
    except Exception as e:
        st.warning(f"Gagal simpan boilerplate ke Sheet: {e}")