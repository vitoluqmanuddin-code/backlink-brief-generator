from typing import cast
from openai.types.chat import ChatCompletionMessageParam
from config import get_client
from prompts import SYSTEM_PROMPT, build_user_prompt


def detect_format(
    serp_data: dict,
    keyword: str,
    api_key: str,
    model: str,
) -> str:
    client = get_client(api_key)

    organic = serp_data.get("organic", [])[:5]
    serp_summary = "\n".join(
        f"{r['position']}. {r['title']} — {r.get('snippet', '')}"
        for r in organic
    )

    user_message = f"""Keyword: {keyword}

Top SERP results:
{serp_summary}

Tentukan format artikel yang paling sesuai berdasarkan pola SERP di atas.
Jawab hanya dengan satu kata: listicle, edukatif, atau how-to."""

    messages = cast(list[ChatCompletionMessageParam], [
        {"role": "system", "content": "You are an SEO content strategist."},
        {"role": "user", "content": user_message},
    ])

    if "gpt" in model.lower():
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=10,
            temperature=0.0,
        )
    else:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=10,
            temperature=0.0,
        )

    raw = (response.choices[0].message.content or "").strip().lower()

    if "listicle" in raw:
        return "listicle"
    elif "how-to" in raw or "how to" in raw:
        return "how-to"
    else:
        return "edukatif"


def generate_brief(
    keyword: str,
    product: str,
    url1: str,
    anchor1: str,
    url2: str,
    anchor2: str,
    target_media: str,
    article_format: str,
    mekari_source: str,
    n_tools: int | None,
    scraped_results: list[dict],
    serp_data: dict | None,
    api_key: str,
    model: str,
) -> tuple[str, object]:
    client = get_client(api_key)

    user_prompt = build_user_prompt(
        keyword=keyword,
        product=product,
        url1=url1,
        anchor1=anchor1,
        url2=url2,
        anchor2=anchor2,
        target_media=target_media,
        article_format=article_format,
        mekari_source=mekari_source,
        n_tools=n_tools,
        scraped_results=scraped_results,
        serp_data=serp_data,
    )

    messages = cast(list[ChatCompletionMessageParam], [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ])

    if "gpt" in model.lower():
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=8000,
            temperature=0.1,
        )
    else:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=8000,
            temperature=0.1,
        )

    usage = response.usage
    return (response.choices[0].message.content or "").strip(), usage