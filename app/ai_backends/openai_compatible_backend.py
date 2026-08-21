"""
用官方 openai SDK、换一个 base_url，覆盖除 Claude 以外的其他供应商——OpenAI 本身、Google
Gemini、DeepSeek、通义千问(DashScope)、xAI Grok、字节豆包(火山方舟) 官方都提供了兼容 OpenAI
调用格式的接口（细节见项目内的架构计划文档），不需要给每家单独写一套 SDK 调用代码。

Uses the official openai SDK with a swapped base_url to cover every provider besides Claude —
OpenAI itself, Google Gemini, DeepSeek, Alibaba Qwen (DashScope), xAI Grok, and ByteDance Doubao
(Volcengine Ark) all officially expose an OpenAI-compatible calling convention, so one client
implementation covers all of them instead of one bespoke SDK integration per company.

这几家对"结构化 JSON 输出"的支持程度不完全一样，用得住的最保险公共选项是 response_format:
{"type": "json_object"}（只保证"是合法JSON"，不保证字段对得上 schema），所以提示词里额外把
期望的字段结构写清楚（见 app/ai_prompts.py 的 json_shape_hint），解析失败就跟 Anthropic 那条
路径一样返回 None，不抛出。

These providers' support for structured JSON output isn't all identical — the safest common
option is response_format: {"type": "json_object"} (guarantees "valid JSON" only, not schema
conformance), so the prompt text also spells out the expected field shape (see
app/ai_prompts.json_shape_hint). Parse failures return None here too, same contract as the
Anthropic path.
"""
import logging

from openai import OpenAI

from app import ai_prompts

logger = logging.getLogger("pubmed_alert.ai.openai_compatible")


def _create_json(settings, prompt, schema, max_tokens):
    client = OpenAI(api_key=settings.ai_api_key, base_url=settings.ai_base_url)
    response = client.chat.completions.create(
        model=settings.ai_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt + ai_prompts.json_shape_hint(schema)}],
        response_format={"type": "json_object"},
    )
    text = response.choices[0].message.content
    try:
        return ai_prompts.parse_json_response(text)
    except Exception:
        # 解析失败时把模型的原始回复记下来（截断到500字防止日志被灌爆）——不然只看得到
        # "JSONDecodeError"，看不出模型到底返回了什么、是被截断了还是夹了别的文字。
        # Log the model's raw reply on parse failure (capped at 500 chars so logs don't flood) —
        # otherwise all you see is "JSONDecodeError" with no visibility into what the model
        # actually returned, or whether it was truncated vs. wrapped in extra text.
        logger.error("could not parse JSON from model response, raw text: %r", (text or "")[:500])
        raise


def enrich_article(article: dict, subscription_topic: str, target_langs, settings) -> dict | None:
    try:
        prompt = ai_prompts.build_enrich_prompt(article, subscription_topic, target_langs)
        schema = ai_prompts.build_enrich_schema(target_langs)
        return _create_json(settings, prompt, schema, max_tokens=4096)
    except Exception:
        logger.exception("enrich_article failed for pmid %s", article.get("pmid"))
        return None


def generate_query(description: str, settings) -> str | None:
    try:
        prompt = ai_prompts.build_query_prompt(description)
        data = _create_json(settings, prompt, ai_prompts.QUERY_SCHEMA, max_tokens=1024)
        return data.get("query") or None
    except Exception:
        logger.exception("generate_query failed")
        return None


def write_trend_digest(subscription_label: str, articles: list, target_langs, settings) -> dict | None:
    try:
        prompt = ai_prompts.build_trend_prompt(subscription_label, articles, target_langs)
        schema = ai_prompts.build_trend_schema(target_langs)
        return _create_json(settings, prompt, schema, max_tokens=6144)
    except Exception:
        logger.exception("write_trend_digest failed for subscription %s", subscription_label)
        return None


def test_connection(settings) -> bool:
    try:
        client = OpenAI(api_key=settings.ai_api_key, base_url=settings.ai_base_url)
        client.chat.completions.create(
            model=settings.ai_model, max_tokens=8,
            messages=[{"role": "user", "content": "Reply with just \"ok\"."}],
        )
        return True
    except Exception:
        logger.exception("test_connection failed")
        return False
