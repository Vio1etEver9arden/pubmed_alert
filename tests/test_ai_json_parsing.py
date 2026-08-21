"""
测试 app/ai_prompts.py 的 parse_json_response()——尽量把 AI 模型的原始回复解析成 JSON。

背景：走 openai 兼容接口的供应商里，Google Gemini 官方文档自己都说"OpenAI 兼容层还在 beta，
功能还在补齐"，实测也确实发现哪怕要求了 response_format: json_object，偶尔还是会返回被截断/
夹带 markdown 代码块的内容，直接 json.loads() 会失败。这个函数就是为了在几种常见的"差一点点
就是合法 JSON"的情况下把内容救回来，救不回来才真正判定为失败。

Tests app/ai_prompts.py's parse_json_response() — best-effort JSON parsing of a model's raw reply.

Background: among providers reached through the openai-compatible path, Google Gemini's own
docs say their OpenAI-compatibility layer is "still beta, feature support still being extended"
— and testing confirmed that even with response_format: json_object requested, it occasionally
returns truncated content or content wrapped in a markdown code fence, which plain json.loads()
fails on. This function recovers from a few common "almost valid JSON" shapes before actually
giving up.
"""
import json

import pytest

from app.ai_prompts import parse_json_response


def test_parses_clean_json_directly():
    text = '{"summary_en": "hello", "relevance_score": 80}'
    assert parse_json_response(text) == {"summary_en": "hello", "relevance_score": 80}


def test_parses_json_wrapped_in_markdown_fence():
    text = '```json\n{"summary_en": "hello", "relevance_score": 80}\n```'
    assert parse_json_response(text) == {"summary_en": "hello", "relevance_score": 80}


def test_parses_json_wrapped_in_plain_fence_without_language_tag():
    text = '```\n{"summary_en": "hello"}\n```'
    assert parse_json_response(text) == {"summary_en": "hello"}


def test_parses_json_with_surrounding_prose():
    text = 'Sure, here is the JSON:\n{"summary_en": "hello"}\nHope that helps!'
    assert parse_json_response(text) == {"summary_en": "hello"}


def test_raises_on_genuinely_truncated_json():
    """真的被截断到没法挽救的情况，应该照常抛出解析错误，让调用方当成"这次失败"处理。
    Genuinely unrecoverable truncation should still raise, so the caller treats it as a failed
    call (returns None).
    """
    text = '{"summary_en": "this got cut off mid-strin'
    with pytest.raises(json.JSONDecodeError):
        parse_json_response(text)
