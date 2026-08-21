"""
所有实际发给 AI 模型的提示词（prompt）文字，集中在这一个文件里。

之所以单独拆出来（而不是散落在 app/ai_backends/ 的两个调用文件里），是因为这些文字才是真正决定
"AI 回答质量好不好、花多少钱"的东西——以后想调优提示词，应该只需要改这一个文件，不需要碰调用
逻辑；`prompt_lab/` 目录测试新的提示词写法时，也是拿这里的函数当基准对照。

Every piece of text actually sent to an AI model lives in this one file (not scattered across the
two files in app/ai_backends/), because this text is what actually determines answer quality and
cost. Tuning prompts later should only ever touch this file, never the calling logic; `prompt_lab/`
uses these same functions as the baseline to compare candidate rewrites against.

三个功能各自的 schema 是"动态"的：是否需要"翻译成本地语言"这件事，取决于调用方算好的
target_langs 列表长度是不是大于1（只有 ["en"] 就是纯英文场景，不问模型要多余的字段，省 token）。
The schema for each of the three enrichment tasks is built dynamically: whether "also translate
into the local language" fields are asked for at all depends on whether the caller-computed
target_langs list has more than one language (just ["en"] means English-only — don't even ask the
model for the extra fields, to save tokens).
"""

import json
import re

LANG_NAMES = {"zh": "Simplified Chinese", "en": "English", "ja": "Japanese"}


def parse_json_response(text: str) -> dict:
    """尽量把模型的原始回复解析成 JSON——先直接解析；不行就去掉可能包着的 ```json ... ``` 代码
    块再试一次；还不行就从第一个 { 到最后一个 } 之间截一段再试一次。全部失败就把最后一次的
    json.JSONDecodeError 原样抛出去，让调用方（backend 模块）按"这次调用失败"处理、返回 None。

    加这一层容错是因为实测发现：走 openai 兼容接口的供应商（这里具体是 Gemini），哪怕已经要求
    了 response_format: json_object，偶尔还是会返回被截断/夹带多余文字的内容——单纯
    json.loads() 直接解析会失败，但这些情况往往简单处理一下就能救回来。

    Best-effort JSON parsing of a model's raw reply — try direct parsing first; if that fails,
    strip a possible ```json ... ``` fence and retry; if that still fails, slice from the first
    { to the last } and retry. If everything fails, re-raises the last json.JSONDecodeError so
    the caller (a backend module) treats this as a failed call and returns None.

    This extra tolerance exists because testing showed that providers reached through the
    openai-compatible path (Gemini, specifically) occasionally return truncated or
    prose-wrapped content even when response_format: json_object was requested — plain
    json.loads() fails outright, but these cases are often recoverable with simple cleanup.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start:end + 1])

    return json.loads(text)  # 让最后一次真实的报错抛出去 let the final real error propagate


def _local_lang_name(target_langs):
    if len(target_langs) <= 1:
        return None
    return LANG_NAMES.get(target_langs[-1], target_langs[-1])


def build_enrich_schema(target_langs) -> dict:
    bilingual = len(target_langs) > 1
    properties = {
        "summary_en": {"type": "string"},
        "relevance_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "keywords": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
    }
    required = ["summary_en", "relevance_score", "keywords"]
    if bilingual:
        properties["summary_local"] = {"type": "string"}
        properties["translated_title"] = {"type": "string"}
        required += ["summary_local", "translated_title"]
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def build_enrich_prompt(article: dict, subscription_topic: str, target_langs) -> str:
    local_lang_name = _local_lang_name(target_langs)
    lines = [
        "You are helping a researcher triage new PubMed articles for a literature-alert subscription.",
        f"Subscription topic: {subscription_topic}",
        f"Article title: {article.get('title') or ''}",
        f"Article abstract: {article.get('abstract') or '(no abstract available)'}",
        "",
        "Return JSON with:",
        "- summary_en: a 1-2 sentence plain-language summary of the article's main finding, in English.",
        "- relevance_score: an integer 0-100 for how relevant this article is to the subscription topic above. "
        "Judge based on topical overlap between the abstract and the subscription topic.",
        "- keywords: up to 8 short English keyword phrases drawn from the abstract "
        "(always in English, regardless of any other language requested below).",
    ]
    if local_lang_name:
        lines += [
            f"- summary_local: the same summary as summary_en, written naturally in {local_lang_name} "
            "(not a literal word-for-word translation).",
            f"- translated_title: the article title translated into {local_lang_name}. "
            f"If the title is already written in {local_lang_name}, return it unchanged.",
        ]
    return "\n".join(lines)


QUERY_SCHEMA = {
    "type": "object",
    "properties": {"query": {"type": "string"}},
    "required": ["query"],
    "additionalProperties": False,
}


def build_query_prompt(description: str) -> str:
    return (
        "You are helping a researcher write a PubMed advanced search query.\n"
        f"Plain-language description of what they want to find: {description}\n\n"
        "Write ONE PubMed search query using proper field tags "
        "(e.g. [Title/Abstract], [Journal], [Author]) and boolean operators (AND/OR/NOT) "
        "combining the relevant concepts. Return JSON with a single field \"query\" containing "
        "only the query string itself — no explanation, no markdown, no surrounding quotes."
    )


def build_trend_schema(target_langs) -> dict:
    bilingual = len(target_langs) > 1
    properties = {"prose_en": {"type": "string"}}
    required = ["prose_en"]
    if bilingual:
        properties["prose_local"] = {"type": "string"}
        required.append("prose_local")
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def build_trend_prompt(subscription_label: str, articles: list, target_langs) -> str:
    local_lang_name = _local_lang_name(target_langs)
    article_lines = "\n".join(
        f"- {a.get('title') or ''}: {(a.get('ai_summary_en') or a.get('abstract') or '')[:300]}"
        for a in articles
    )
    lines = [
        f'You are writing a monthly research-trend digest for a PubMed subscription named "{subscription_label}".',
        f"Here are the {len(articles)} articles discovered this month:",
        article_lines,
        "",
        "Write a short prose synthesis (2-4 paragraphs) of the notable themes, directions, or "
        "recurring topics across these articles — something a busy researcher can skim to catch "
        "up on a month's worth of literature in this area.",
        "",
        "Return JSON with:",
        "- prose_en: the synthesis written in English.",
    ]
    if local_lang_name:
        lines.append(
            f"- prose_local: the same synthesis written naturally in {local_lang_name} "
            "(not a literal word-for-word translation)."
        )
    return "\n".join(lines)


# openai_compatible 后端不强制服务端 JSON schema 校验（只用 response_format: json_object 保证
# "是合法 JSON"），所以额外在提示词里显式描述一遍期望的字段结构，降低模型输出格式跑偏的概率。
# The openai_compatible backend has no server-enforced JSON schema (response_format: json_object
# only guarantees "valid JSON") — so the expected field shape is spelled out again in the prompt
# text, to reduce the chance the model drifts from the expected structure.
def json_shape_hint(schema: dict) -> str:
    fields = ", ".join(schema["properties"].keys())
    return f"\n\nRespond with ONLY a JSON object with exactly these fields: {fields}. No other text."
