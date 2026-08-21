"""
用官方 anthropic SDK 调用 Claude。用 output_config 的 json_schema 结构化输出——由 Anthropic
服务端保证回复一定是合法 JSON、且字段跟 schema 对得上，比"提示词里描述一遍指望模型照做"更可靠，
所以 Claude 这条路径优先用这个。

Calls Claude via the official anthropic SDK. Uses output_config's json_schema structured output —
Anthropic's server guarantees the reply is valid JSON matching the schema, which is more reliable
than "describe the shape in the prompt and hope the model follows it", so this path uses it.

任何失败（网络、鉴权、限流、JSON 解析）都在这里兜住，返回 None，不抛出到调用方——这是这整个
AI 功能模块的约定：AI 是锦上添花的功能，出错了大不了这次没有 AI 内容，不能影响检索/发信主流程。
Every failure (network, auth, rate limit, JSON parsing) is caught here and returns None instead of
raising — the whole AI feature set's contract: AI is a nice-to-have, a failure just means no AI
content this time, it must never break the core poll/send flow.
"""
import logging

import anthropic

from app import ai_prompts

logger = logging.getLogger("pubmed_alert.ai.anthropic")


def _create_json(settings, prompt, schema, max_tokens):
    client = anthropic.Anthropic(api_key=settings.ai_api_key)
    response = client.messages.create(
        model=settings.ai_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    text = next(b.text for b in response.content if b.type == "text")
    try:
        return ai_prompts.parse_json_response(text)
    except Exception:
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
        client = anthropic.Anthropic(api_key=settings.ai_api_key)
        client.messages.create(
            model=settings.ai_model, max_tokens=8,
            messages=[{"role": "user", "content": "Reply with just \"ok\"."}],
        )
        return True
    except Exception:
        logger.exception("test_connection failed")
        return False
