"""
拿 fixtures.py 里的真实文章样本，跑一遍 app/ai_prompts.py 里当前的提示词（走 app/ai.py 真实的
调用路径，不是另外写一套逻辑），打印每次调用的输出，方便肉眼判断质量。

Runs the current prompts from app/ai_prompts.py (via the real app/ai.py call path — not a
separate reimplementation) against the sample articles in fixtures.py, printing each call's
output so quality can be judged by eye.

**默认不会产生任何真实调用**：脚本顶部检查有没有配置 API Key，没有就打印提示直接退出。
**Makes no real API calls by default**: checks for a configured API key at startup and exits
with instructions if none is set.

用法 / Usage:
  export PROMPT_LAB_BACKEND=anthropic          # or: openai_compatible
  export PROMPT_LAB_API_KEY=sk-...
  export PROMPT_LAB_BASE_URL=...               # only needed for openai_compatible
  export PROMPT_LAB_MODEL=claude-haiku-4-5
  python3 prompt_lab/run_comparison.py

跑一次大概花多少钱：每篇样本文章一次 enrich_article 调用，用 Haiku 档位模型的话通常远低于
$0.01；具体看 fixtures.py 里放了几篇样本、摘要多长。
Rough cost per run: one enrich_article call per sample article — typically well under $0.01 with
a Haiku-tier model; exact cost depends on how many samples are in fixtures.py and how long their
abstracts are.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fixtures import SAMPLE_ARTICLES  # noqa: E402
from app import ai  # noqa: E402


def _settings_from_env():
    return SimpleNamespace(
        ai_backend=os.environ.get("PROMPT_LAB_BACKEND", "anthropic"),
        ai_api_key=os.environ.get("PROMPT_LAB_API_KEY", ""),
        ai_base_url=os.environ.get("PROMPT_LAB_BASE_URL", ""),
        ai_model=os.environ.get("PROMPT_LAB_MODEL", "claude-haiku-4-5"),
    )


def main():
    settings = _settings_from_env()
    if not ai.is_configured(settings):
        print(
            "没有配置 API Key，不会产生真实调用。设置 PROMPT_LAB_API_KEY（openai_compatible 后端"
            "还需要 PROMPT_LAB_BASE_URL）之后再运行这个脚本。\n"
            "Not configured — no real calls will be made. Set PROMPT_LAB_API_KEY (and "
            "PROMPT_LAB_BASE_URL for the openai_compatible backend) before running this script."
        )
        return

    for article in SAMPLE_ARTICLES:
        print(f"\n=== {article['title'][:70]} ===")
        result = ai.enrich_article(article, article["subscription_topic"], ["en"], settings)
        if result is None:
            print("  call failed — see logged exception")
            continue
        print("  summary_en:", result.get("summary_en"))
        print("  relevance_score:", result.get("relevance_score"))
        print("  keywords:", result.get("keywords"))


if __name__ == "__main__":
    main()
