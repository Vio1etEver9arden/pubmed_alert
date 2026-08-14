"""
AI 摘要总结接口占位。目前未接入任何大模型，summarize() 始终返回 None，
邮件模板会因此跳过"AI 总结"这部分内容。以后想接入时，只需要实现这个函数。
Reserved interface for AI-generated summaries. Not wired to any LLM yet — summarize()
always returns None, so the email template simply skips the "AI summary" section.
To add a provider later, just implement this function's body.

示例实现 / Example implementation (Anthropic Claude):

    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def summarize(article: dict) -> str | None:
        prompt = f"用1-2句话总结这篇论文的核心发现：\\n标题: {article['title']}\\n摘要: {article['abstract']}"
        resp = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text
"""


def summarize(article: dict):
    return None
