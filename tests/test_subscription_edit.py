"""
测试"编辑订阅"会不会正确重置 initial_poll_done。

背景：编辑订阅时如果关键词/期刊/作者/自定义检索式真的变了，应该把这个订阅标记成"还没做过首次
检索"（initial_poll_done = False），这样下次检索会走"发一批入门文献（最多30篇左右）"这条路，
而不是把新检索式匹配到的几十上百篇历史文献全部当"新发现"一次性发邮件——这正是用户报告的那个
"改一下关键词就收到接近100篇邮件"的 bug 的根本原因。只改标签/收件邮箱/频率这些不影响检索结果
的字段，不应该触发这个重置。

Tests that editing a subscription correctly resets initial_poll_done.

Background: if a subscription's keywords/journals/authors/custom query actually change during an
edit, the subscription should be marked as "hasn't done its first poll yet" (initial_poll_done =
False), so the next poll sends one starter batch (capped around 30 articles) instead of treating
every historical match under the new query as a "newly found" article and dumping them all into
one email — this is the exact root cause of the "editing keywords floods me with ~100 articles"
bug the user reported. Changing only fields that don't affect search results (label, recipient
email, frequency) should not trigger this reset.
"""
from tests.conftest import register_and_login
from app.db import Subscription


def _create_subscription(client, **overrides):
    data = {
        "label": "Test subscription", "keywords": "CRISPR", "journals": "", "authors": "",
        "query_override": "", "recipient_email": "a@example.com", "frequency": "weekly",
    }
    data.update(overrides)
    return client.post("/subscriptions/new", data=data)


def _edit_subscription(client, sub_id, **overrides):
    data = {
        "label": "Test subscription", "keywords": "CRISPR", "journals": "", "authors": "",
        "query_override": "", "recipient_email": "a@example.com", "frequency": "weekly",
    }
    data.update(overrides)
    return client.post(f"/subscriptions/{sub_id}/edit", data=data)


def test_changing_keywords_resets_initial_poll_done(client, db_session):
    register_and_login(client, db_session, "alice", "alice@example.com")
    _create_subscription(client)
    sub = db_session.query(Subscription).first()
    sub.initial_poll_done = True
    db_session.commit()

    _edit_subscription(client, sub.id, keywords="single-cell RNA sequencing")

    db_session.refresh(sub)
    assert sub.initial_poll_done is False


def test_changing_journals_resets_initial_poll_done(client, db_session):
    register_and_login(client, db_session, "alice", "alice@example.com")
    _create_subscription(client)
    sub = db_session.query(Subscription).first()
    sub.initial_poll_done = True
    db_session.commit()

    _edit_subscription(client, sub.id, journals="Nature")

    db_session.refresh(sub)
    assert sub.initial_poll_done is False


def test_changing_query_override_resets_initial_poll_done(client, db_session):
    register_and_login(client, db_session, "alice", "alice@example.com")
    _create_subscription(client)
    sub = db_session.query(Subscription).first()
    sub.initial_poll_done = True
    db_session.commit()

    _edit_subscription(client, sub.id, query_override='("CRISPR"[Title/Abstract])')

    db_session.refresh(sub)
    assert sub.initial_poll_done is False


def test_changing_only_label_does_not_reset_initial_poll_done(client, db_session):
    register_and_login(client, db_session, "alice", "alice@example.com")
    _create_subscription(client)
    sub = db_session.query(Subscription).first()
    sub.initial_poll_done = True
    db_session.commit()

    _edit_subscription(client, sub.id, label="Renamed subscription")

    db_session.refresh(sub)
    assert sub.initial_poll_done is True
    assert sub.label == "Renamed subscription"


def test_changing_only_recipient_or_frequency_does_not_reset_initial_poll_done(client, db_session):
    register_and_login(client, db_session, "alice", "alice@example.com")
    _create_subscription(client)
    sub = db_session.query(Subscription).first()
    sub.initial_poll_done = True
    db_session.commit()

    _edit_subscription(client, sub.id, recipient_email="new@example.com", frequency="daily")

    db_session.refresh(sub)
    assert sub.initial_poll_done is True


def test_resaving_identical_criteria_does_not_reset_initial_poll_done(client, db_session):
    """提交表单时哪怕内容跟原来完全一样（用户就是点了一下保存），也不应该误判成"变了"。
    Even resubmitting the exact same values (the user just clicked save) shouldn't be mistaken
    for a real change.
    """
    register_and_login(client, db_session, "alice", "alice@example.com")
    _create_subscription(client, keywords="CRISPR")
    sub = db_session.query(Subscription).first()
    sub.initial_poll_done = True
    db_session.commit()

    _edit_subscription(client, sub.id, keywords="CRISPR")

    db_session.refresh(sub)
    assert sub.initial_poll_done is True
