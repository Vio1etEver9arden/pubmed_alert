"""
测试邮件正文的"最多完整展示几篇文章"这个上限（app/mailer.py 的 EMAIL_MAX_ARTICLES）。

背景：Gmail 等邮箱客户端对邮件正文大小有硬性限制（Gmail 大约 102KB），超过会被"裁剪"，只显示
前面一部分。加了 AI 总结/关键词/翻译标题之后每篇文章占的篇幅变大了不少，用户反馈过一次检索
发现很多新文章时邮件显示不全——这就是原因。修复方式是邮件正文最多完整展示 EMAIL_MAX_ARTICLES
篇，超出的部分只提示"还有 N 篇未显示"，并给一个链接去网页看完整列表。

Tests the cap on how many articles are fully rendered in one email body
(app/mailer.py's EMAIL_MAX_ARTICLES).

Background: email clients like Gmail enforce a hard size limit on the message body (roughly
102KB for Gmail) — messages over that get clipped, showing only the beginning. Since AI
summaries/keywords/translated titles were added, each article takes up noticeably more space,
and a user reported that a poll finding many new articles produced an email that didn't display
completely — that's this. The fix caps the email body at EMAIL_MAX_ARTICLES fully-rendered
articles, with a "N more not shown" note and a link to the full list on the web for the rest.
"""
from types import SimpleNamespace

from app.mailer import render_digest_html, EMAIL_MAX_ARTICLES


def _make_article(i):
    return SimpleNamespace(
        id=i, title=f"Article {i}", authors="A", journal="J", pub_date="2026",
        jcr_quartile=None, jif=None, doi=None, abstract=None,
        initial_relevant=False, initial_recent=False, pubmed_url=f"https://x/{i}",
        oa_pdf_url=None, duplicate_labels=None,
        ai_summary_en=None, ai_summary_local=None, ai_relevance_score=None,
        ai_translated_title=None, ai_keywords=[],
    )


def test_below_cap_shows_everything_with_no_note():
    sub = SimpleNamespace(id=1, label="Test", user_id=1)
    articles = [_make_article(i) for i in range(5)]
    html = render_digest_html(sub, articles, "en")
    for i in range(5):
        assert f"Article {i}" in html
    assert "aren't fully shown" not in html


def test_above_cap_truncates_and_shows_note_with_correct_count():
    sub = SimpleNamespace(id=1, label="Test", user_id=1)
    total = EMAIL_MAX_ARTICLES + 7
    articles = [_make_article(i) for i in range(total)]
    html = render_digest_html(sub, articles, "en")

    for i in range(EMAIL_MAX_ARTICLES):
        assert f"Article {i}" in html
    for i in range(EMAIL_MAX_ARTICLES, total):
        assert f"Article {i}" not in html
    # Jinja 会自动把撇号转义成 &#39;（跟之前 "Alice's subscription" 那次踩的坑一样）。
    # Jinja auto-escapes the apostrophe to &#39; (the same escaping gotcha as the earlier
    # "Alice's subscription" test).
    assert "7 more article(s) aren&#39;t fully shown" in html


def test_view_all_link_points_at_the_subscriptions_preview_page():
    sub = SimpleNamespace(id=99, label="Test", user_id=1)
    articles = [_make_article(i) for i in range(EMAIL_MAX_ARTICLES + 1)]
    html = render_digest_html(sub, articles, "en")
    assert "/subscriptions/99/preview" in html
