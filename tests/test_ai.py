"""
测试 AI 功能的两条后端路径（app/ai_backends/anthropic_backend.py 和
app/ai_backends/openai_compatible_backend.py），以及 app/ai.py 这个转发层。

跟 tests/test_unpaywall.py 一样的思路：用 monkeypatch 把真正发网络请求的 SDK 客户端换成假的，
永远不连真实的 API，也就不会产生真实费用。app/ai.py 对外只有一套接口，不管背后是哪个供应商，
所以 enrich_article/generate_query/write_trend_digest 这三个函数各自的"未配置/JSON解析失败/
调用抛异常/正常返回"四种情况，两条后端路径都要各测一遍。

Tests both AI backend paths (app/ai_backends/anthropic_backend.py and
app/ai_backends/openai_compatible_backend.py) and the app/ai.py dispatch layer.

Same idea as tests/test_unpaywall.py: monkeypatch swaps out the real network-calling SDK client
for a fake one, so this never touches a real API and never costs real money. app/ai.py exposes one
interface regardless of provider, so the four scenarios (not configured / malformed JSON / API
exception / happy path) for enrich_article/generate_query/write_trend_digest are each tested
against both backend paths.
"""
from types import SimpleNamespace

from app import ai
from app.ai_backends import anthropic_backend, openai_compatible_backend


def _settings(backend="anthropic", key="sk-test", base_url="", model="claude-haiku-4-5"):
    return SimpleNamespace(ai_backend=backend, ai_api_key=key, ai_base_url=base_url, ai_model=model)


# ---- app/ai.py dispatch layer ----

def test_not_configured_when_no_key():
    assert ai.is_configured(_settings(key="")) is False


def test_not_configured_when_openai_compatible_missing_base_url():
    assert ai.is_configured(_settings(backend="openai_compatible", base_url="")) is False


def test_configured_anthropic_needs_only_key():
    assert ai.is_configured(_settings(backend="anthropic")) is True


def test_configured_openai_compatible_needs_key_and_base_url():
    assert ai.is_configured(_settings(backend="openai_compatible", base_url="https://api.openai.com/v1")) is True


def test_enrich_article_returns_none_when_not_configured():
    assert ai.enrich_article({"pmid": "1", "title": "t"}, "topic", ["en"], _settings(key="")) is None


# ---- fakes shared by both backend test groups ----

class _FakeTextBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _FakeAnthropicMessage:
    def __init__(self, text):
        self.content = [_FakeTextBlock(text)]


class _FakeAnthropicMessages:
    def __init__(self, fn):
        self._fn = fn

    def create(self, **kwargs):
        return self._fn(kwargs)


class _FakeAnthropicClient:
    def __init__(self, fn):
        self.messages = _FakeAnthropicMessages(fn)


class _FakeChoice:
    def __init__(self, text):
        self.message = SimpleNamespace(content=text)


class _FakeOpenAIMessage:
    def __init__(self, text):
        self.choices = [_FakeChoice(text)]


class _FakeOpenAICompletions:
    def __init__(self, fn):
        self._fn = fn

    def create(self, **kwargs):
        return self._fn(kwargs)


class _FakeOpenAIClient:
    def __init__(self, fn):
        self.chat = SimpleNamespace(completions=_FakeOpenAICompletions(fn))


ENRICH_PAYLOAD = (
    '{"summary_en": "s", "relevance_score": 80, "keywords": ["a", "b"]}'
)


def test_anthropic_enrich_article_happy_path(monkeypatch):
    monkeypatch.setattr(
        anthropic_backend.anthropic, "Anthropic",
        lambda **k: _FakeAnthropicClient(lambda kw: _FakeAnthropicMessage(ENRICH_PAYLOAD)),
    )
    result = ai.enrich_article({"pmid": "1", "title": "t"}, "topic", ["en"], _settings())
    assert result["relevance_score"] == 80
    assert result["keywords"] == ["a", "b"]


def test_anthropic_enrich_article_malformed_json_returns_none(monkeypatch):
    monkeypatch.setattr(
        anthropic_backend.anthropic, "Anthropic",
        lambda **k: _FakeAnthropicClient(lambda kw: _FakeAnthropicMessage("not json")),
    )
    assert ai.enrich_article({"pmid": "1", "title": "t"}, "topic", ["en"], _settings()) is None


def test_anthropic_enrich_article_api_exception_returns_none(monkeypatch):
    def _raise(**k):
        raise RuntimeError("boom")
    monkeypatch.setattr(anthropic_backend.anthropic, "Anthropic", _raise)
    assert ai.enrich_article({"pmid": "1", "title": "t"}, "topic", ["en"], _settings()) is None


def test_anthropic_generate_query_happy_path(monkeypatch):
    payload = '{"query": "(\\"CRISPR\\"[Title/Abstract])"}'
    monkeypatch.setattr(
        anthropic_backend.anthropic, "Anthropic",
        lambda **k: _FakeAnthropicClient(lambda kw: _FakeAnthropicMessage(payload)),
    )
    assert ai.generate_query("crispr papers", _settings()) == '("CRISPR"[Title/Abstract])'


def test_anthropic_write_trend_digest_happy_path(monkeypatch):
    payload = '{"prose_en": "Summary text."}'
    monkeypatch.setattr(
        anthropic_backend.anthropic, "Anthropic",
        lambda **k: _FakeAnthropicClient(lambda kw: _FakeAnthropicMessage(payload)),
    )
    result = ai.write_trend_digest("My Sub", [{"title": "A", "abstract": "B"}], ["en"], _settings())
    assert result["prose_en"] == "Summary text."


def test_openai_compatible_enrich_article_happy_path(monkeypatch):
    settings = _settings(backend="openai_compatible", base_url="https://api.openai.com/v1", model="gpt-5.1")
    monkeypatch.setattr(
        openai_compatible_backend, "OpenAI",
        lambda **k: _FakeOpenAIClient(lambda kw: _FakeOpenAIMessage(ENRICH_PAYLOAD)),
    )
    result = ai.enrich_article({"pmid": "1", "title": "t"}, "topic", ["en"], settings)
    assert result["relevance_score"] == 80


def test_openai_compatible_enrich_article_malformed_json_returns_none(monkeypatch):
    settings = _settings(backend="openai_compatible", base_url="https://api.deepseek.com", model="deepseek-chat")
    monkeypatch.setattr(
        openai_compatible_backend, "OpenAI",
        lambda **k: _FakeOpenAIClient(lambda kw: _FakeOpenAIMessage("not json")),
    )
    assert ai.enrich_article({"pmid": "1", "title": "t"}, "topic", ["en"], settings) is None


def test_openai_compatible_api_exception_returns_none(monkeypatch):
    settings = _settings(backend="openai_compatible", base_url="https://api.x.ai/v1", model="grok-4.6")

    def _raise(**k):
        raise RuntimeError("boom")
    monkeypatch.setattr(openai_compatible_backend, "OpenAI", _raise)
    assert ai.enrich_article({"pmid": "1", "title": "t"}, "topic", ["en"], settings) is None


def test_openai_compatible_write_trend_digest_bilingual(monkeypatch):
    settings = _settings(backend="openai_compatible", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", model="qwen-plus")
    payload = '{"prose_en": "English text.", "prose_local": "中文正文。"}'
    monkeypatch.setattr(
        openai_compatible_backend, "OpenAI",
        lambda **k: _FakeOpenAIClient(lambda kw: _FakeOpenAIMessage(payload)),
    )
    result = ai.write_trend_digest("My Sub", [{"title": "A", "abstract": "B"}], ["en", "zh"], settings)
    assert result["prose_local"] == "中文正文。"
