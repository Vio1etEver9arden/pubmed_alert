"""
AI 功能对外的统一入口。这个模块本身不直接调用任何一家 AI 的 SDK——只根据
`settings.ai_backend` 转发给 app/ai_backends/ 下面对应的实现（"anthropic" 或
"openai_compatible"）。调用方（scheduler.py、main.py）永远只认这一个模块，不需要关心用户配的
到底是 Claude 还是 DeepSeek 还是别的什么牌子。

The single entry point for AI features. This module never calls any AI SDK directly — it just
dispatches to the matching implementation under app/ai_backends/ based on `settings.ai_backend`
("anthropic" or "openai_compatible"). Callers (scheduler.py, main.py) only ever talk to this
module and don't need to know or care whether the user configured Claude, DeepSeek, or anything
else.

AI 功能整体是"按用户自愿开启"的：没配置 key 就完全没有这些功能，`is_configured()` 返回 False，
调用方应该照常运行、只是拿不到 AI 内容——不是报错状态。
AI features are entirely opt-in per user: no key configured means the features are simply absent
— `is_configured()` returns False, callers should proceed normally and just get no AI content,
not an error state.
"""
from app.ai_backends import anthropic_backend, openai_compatible_backend

AI_MODEL_CHOICES = ["claude-haiku-4-5", "claude-sonnet-5", "claude-opus-5"]


def _backend(settings):
    return anthropic_backend if settings.ai_backend == "anthropic" else openai_compatible_backend


def is_configured(settings) -> bool:
    if not settings.ai_api_key:
        return False
    return settings.ai_backend == "anthropic" or bool(settings.ai_base_url)


def enrich_article(article: dict, subscription_topic: str, target_langs, settings) -> dict | None:
    if not is_configured(settings):
        return None
    return _backend(settings).enrich_article(article, subscription_topic, target_langs, settings)


def generate_query(description: str, settings) -> str | None:
    if not is_configured(settings):
        return None
    return _backend(settings).generate_query(description, settings)


def write_trend_digest(subscription_label: str, articles: list, target_langs, settings) -> dict | None:
    if not is_configured(settings):
        return None
    return _backend(settings).write_trend_digest(subscription_label, articles, target_langs, settings)


def test_connection(settings) -> bool:
    if not is_configured(settings):
        return False
    return _backend(settings).test_connection(settings)
