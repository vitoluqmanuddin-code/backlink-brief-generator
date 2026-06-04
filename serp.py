import httpx

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"

def fetch_serp(keyword: str, api_key: str, lang: str = "id", country: str = "id", num: int = 10) -> dict:
    """
    Returns:
        {
            "organic": [...],
            "people_also_ask": [...],
            "related_searches": [...]
        }
    """
    params = {
        "q":       keyword,
        "api_key": api_key,
        "hl":      lang,
        "gl":      country,
        "num":     num,
        "engine":  "google",
    }

    try:
        r = httpx.get(SERPAPI_ENDPOINT, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()

        organic = []
        for item in data.get("organic_results", [])[:num]:
            organic.append({
                "position": item.get("position"),
                "title":    item.get("title", ""),
                "url":      item.get("link", ""),
                "snippet":  item.get("snippet", ""),
            })

        people_also_ask = []
        for item in data.get("related_questions", []):
            people_also_ask.append({
                "question": item.get("question", ""),
                "snippet":  item.get("snippet", ""),
            })

        related_searches = []
        for item in data.get("related_searches", []):
            query = item.get("query", "")
            if query:
                related_searches.append(query)

        return {
            "organic":         organic,
            "people_also_ask": people_also_ask,
            "related_searches": related_searches,
        }

    except Exception as e:
        raise RuntimeError(f"SerpApi error: {e}")
