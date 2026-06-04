from openai import OpenAI

# ── Models ────────────────────────────────────────────────────────────────────
MODELS = {
    "Claude Sonnet 4.6 (Default)": "claude-sonnet-4-6",
    "Claude Sonnet 4.5":           "claude-sonnet-4-5",
    "Claude Haiku 4.5 (Cheapest)": "claude-haiku-4-5",
    "GPT-5.1":                     "gpt-5.1",
    "GPT-5.2":                     "gpt-5.2",
}

DEFAULT_MODEL = "claude-sonnet-4-6"

# ── API ───────────────────────────────────────────────────────────────────────
BASE_URL = "https://ai.dinoiki.com/v1"

def get_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=BASE_URL)

# ── Article formats ───────────────────────────────────────────────────────────
FORMATS = {
    "auto":     "Auto-detect via SERP",
    "listicle": "Listicle",
    "edukatif": "Edukatif / Thought Leadership",
    "how-to":   "How-To / Teknis",
}

# ── Mekari products ───────────────────────────────────────────────────────────
PRODUCTS = [
    "Mekari Expense",
    "Mekari Talenta",
    "Mekari Qontak",
    "Mekari Officeless",
    "Mekari",
]

# ── Pricing (USD per 1M tokens) ───────────────────────────────────────────────
MODEL_PRICING = {
    "claude-sonnet-4-6": {"input": 3.00,  "output": 15.00},
    "claude-sonnet-4-5": {"input": 3.00,  "output": 15.00},
    "claude-haiku-4-5":  {"input": 1.00,  "output": 5.00},
    "gpt-5.1":           {"input": 1.25,  "output": 10.00},
    "gpt-5.2":           {"input": 1.75,  "output": 14.00},
}

def calculate_cost(model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model_id)
    if not pricing:
        return 0.0
    input_cost  = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost