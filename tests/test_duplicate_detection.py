"""
测试"同一篇文章命中同一用户名下多个订阅"的检测逻辑（app/scheduler.py 的
_cross_subscription_labels）。这个函数只负责查询、返回一个订阅名字的列表，不碰邮件发送，
所以可以直接用数据库会话测，不需要走注册/登录这些步骤。

Tests for the "same article matched by more than one of this user's subscriptions" detection
(app/scheduler.py's _cross_subscription_labels). This function only queries and returns a list
of subscription labels — no email sending involved — so it can be tested directly against a
database session, without going through registration/login.
"""
from app.db import Subscription, SeenArticle
from app.scheduler import _cross_subscription_labels


def _make_subscription(db_session, user_id, label):
    sub = Subscription(user_id=user_id, label=label, recipient_email="a@example.com")
    db_session.add(sub)
    db_session.commit()
    return sub


def test_finds_labels_of_other_subscriptions_with_the_same_pmid(db_session):
    sub_a = _make_subscription(db_session, user_id=1, label="Keyword search")
    sub_b = _make_subscription(db_session, user_id=1, label="Journal watch")
    db_session.add(SeenArticle(subscription_id=sub_a.id, pmid="12345", title="Shared paper"))
    db_session.add(SeenArticle(subscription_id=sub_b.id, pmid="12345", title="Shared paper"))
    db_session.commit()

    labels = _cross_subscription_labels(
        db_session, user_id=1, pmid="12345", exclude_subscription_id=sub_a.id
    )
    assert labels == ["Journal watch"]


def test_returns_empty_list_when_no_other_subscription_has_seen_it(db_session):
    sub = _make_subscription(db_session, user_id=1, label="Solo subscription")
    db_session.add(SeenArticle(subscription_id=sub.id, pmid="99999", title="Unique paper"))
    db_session.commit()

    labels = _cross_subscription_labels(
        db_session, user_id=1, pmid="99999", exclude_subscription_id=sub.id
    )
    assert labels == []


def test_does_not_cross_user_boundaries(db_session):
    """A 用户不应该因为 B 用户名下有同一篇文章的订阅，就看到 B 的订阅名字。
    User A shouldn't see user B's subscription label just because B also has a subscription
    that matched the same article.
    """
    sub_alice = _make_subscription(db_session, user_id=1, label="Alice's subscription")
    sub_bob = _make_subscription(db_session, user_id=2, label="Bob's subscription")
    db_session.add(SeenArticle(subscription_id=sub_alice.id, pmid="55555", title="Paper"))
    db_session.add(SeenArticle(subscription_id=sub_bob.id, pmid="55555", title="Paper"))
    db_session.commit()

    labels = _cross_subscription_labels(
        db_session, user_id=1, pmid="55555", exclude_subscription_id=sub_alice.id
    )
    assert labels == []
