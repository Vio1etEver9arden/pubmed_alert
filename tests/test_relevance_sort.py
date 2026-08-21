"""
测试待发送文献按 AI 相关性打分从高到低排序（app/scheduler.py 的 dispatch_subscription）。

没打分的文章（没配置 AI，或者是配置 AI 之前就发现的老文章）分数是 NULL，排序时应该自然排到
最后、并按发现时间顺序回退——不需要额外判断"有没有配置 AI"，因为 SQL 对 NULL 排序本来就是
这样处理的。这个测试直接验证这个行为，不依赖真的调用过 AI。

Tests that pending articles are sorted by AI relevance score, highest first
(app/scheduler.py's dispatch_subscription).

Unscored articles (AI not configured, or discovered before AI was enabled) have a NULL score,
which should sort last and fall back to discovery-time order — no separate "is AI configured"
branch needed, since that's just how SQL sorts NULLs. This test verifies that behavior directly,
without needing a real AI call to have happened.
"""
import datetime as dt
from types import SimpleNamespace

from app.db import Subscription, SeenArticle
from app.scheduler import dispatch_subscription
from app import mailer


def _make_subscription(db_session, label="Test", recipient="a@example.com"):
    sub = Subscription(user_id=1, label=label, recipient_email=recipient)
    db_session.add(sub)
    db_session.commit()
    return sub


def _settings():
    return SimpleNamespace(
        smtp_host="smtp.example.com", smtp_port=587, smtp_use_ssl=False,
        sender_email="a@example.com", sender_password="pw", ui_language="en",
    )


def test_higher_relevance_articles_come_first(db_session, monkeypatch):
    sub = _make_subscription(db_session)
    base_time = dt.datetime(2026, 1, 1)
    db_session.add_all([
        SeenArticle(subscription_id=sub.id, pmid="1", title="Low relevance", ai_relevance_score=20,
                    first_seen_at=base_time),
        SeenArticle(subscription_id=sub.id, pmid="2", title="High relevance", ai_relevance_score=90,
                    first_seen_at=base_time + dt.timedelta(minutes=1)),
        SeenArticle(subscription_id=sub.id, pmid="3", title="Mid relevance", ai_relevance_score=50,
                    first_seen_at=base_time + dt.timedelta(minutes=2)),
    ])
    db_session.commit()

    captured = {}

    def fake_send_digest(settings, subscription, articles):
        captured["titles"] = [a.title for a in articles]

    monkeypatch.setattr(mailer, "send_digest", fake_send_digest)

    dispatch_subscription(db_session, sub, _settings())

    assert captured["titles"] == ["High relevance", "Mid relevance", "Low relevance"]


def test_unscored_articles_fall_back_to_discovery_order(db_session, monkeypatch):
    """没配置 AI 的场景：所有分数都是 None，应该退回到"先发现先发送"的老顺序。
    The no-AI-configured scenario: every score is None, should fall back to the original
    discovered-first-sent-first order.
    """
    sub = _make_subscription(db_session)
    base_time = dt.datetime(2026, 1, 1)
    db_session.add_all([
        SeenArticle(subscription_id=sub.id, pmid="1", title="First found",
                    first_seen_at=base_time),
        SeenArticle(subscription_id=sub.id, pmid="2", title="Second found",
                    first_seen_at=base_time + dt.timedelta(minutes=1)),
        SeenArticle(subscription_id=sub.id, pmid="3", title="Third found",
                    first_seen_at=base_time + dt.timedelta(minutes=2)),
    ])
    db_session.commit()

    captured = {}

    def fake_send_digest(settings, subscription, articles):
        captured["titles"] = [a.title for a in articles]

    monkeypatch.setattr(mailer, "send_digest", fake_send_digest)

    dispatch_subscription(db_session, sub, _settings())

    assert captured["titles"] == ["First found", "Second found", "Third found"]


def test_scored_articles_come_before_unscored_legacy_ones(db_session, monkeypatch):
    """混合场景：有的文章打过分（后来才配置AI），有的是配置AI之前的老文章（分数是None）——
    打过分的应该排在前面，没打分的老文章跟在后面。
    Mixed scenario: some articles have a score (AI configured later), some are old articles from
    before AI was enabled (score is None) — scored ones should sort ahead of the unscored legacy
    ones.
    """
    sub = _make_subscription(db_session)
    base_time = dt.datetime(2026, 1, 1)
    db_session.add_all([
        SeenArticle(subscription_id=sub.id, pmid="1", title="Old unscored article",
                    first_seen_at=base_time),
        SeenArticle(subscription_id=sub.id, pmid="2", title="New scored article", ai_relevance_score=60,
                    first_seen_at=base_time + dt.timedelta(minutes=1)),
    ])
    db_session.commit()

    captured = {}

    def fake_send_digest(settings, subscription, articles):
        captured["titles"] = [a.title for a in articles]

    monkeypatch.setattr(mailer, "send_digest", fake_send_digest)

    dispatch_subscription(db_session, sub, _settings())

    assert captured["titles"] == ["New scored article", "Old unscored article"]
