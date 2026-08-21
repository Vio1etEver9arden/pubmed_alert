"""
测试"所有权"：A 用户的订阅/文献，B 用户不应该能看到、也不应该能改。

这类 bug 专业上叫 IDOR（改一下网址里的编号，就能操作别人的数据）——这个项目早期真的出现过这个
漏洞（在加登录系统之前），后来修掉了。这些测试就是为了以后不管怎么改代码，这个漏洞都不会
"悄悄地"再冒出来——如果哪次改动不小心把权限检查删掉了，这些测试会立刻失败，而不是等到真的有人
利用这个漏洞才发现。

Tests for "ownership": user B should never be able to see or modify user A's subscriptions or
articles.

This class of bug is professionally called IDOR (edit a number in the URL, operate on someone
else's data) — this project genuinely had this bug early on (before the login system existed),
and it got fixed. These tests exist so that no matter how the code changes later, this bug can
never quietly creep back in — if some future change accidentally removes an ownership check,
these tests fail immediately, instead of waiting for someone to actually exploit it.
"""
from tests.conftest import register_and_login


def _create_subscription(client, label="Test subscription", recipient="a@example.com"):
    return client.post("/subscriptions/new", data={
        "label": label,
        "keywords": "CRISPR",
        "journals": "",
        "authors": "",
        "query_override": "",
        "recipient_email": recipient,
        "frequency": "weekly",
    })


def test_logged_out_visitor_is_redirected_to_login(client, db_session):
    """完全没登录的人访问首页，应该被送去登录页，而不是能直接看到订阅列表。
    A visitor with no login at all should be sent to the login page, not shown the subscription
    list directly.
    """
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_user_only_sees_their_own_subscriptions(client, db_session):
    register_and_login(client, db_session, "alice", "alice@example.com")
    _create_subscription(client, label="Alice subscription")

    response = client.get("/")
    assert "Alice subscription" in response.text


def test_user_cannot_edit_someone_elses_subscription(client, db_session):
    """核心测试：B 用户不能通过猜 URL 里的编号去编辑 A 用户的订阅。
    The core test: user B can't guess the URL's ID number to edit user A's subscription.
    """
    register_and_login(client, db_session, "alice", "alice@example.com")
    _create_subscription(client)

    from app.db import Subscription
    sub_id = db_session.query(Subscription).first().id

    # 换成另一个账号 / switch to a different account
    register_and_login(client, db_session, "bob", "bob@example.com")

    edit_page = client.get(f"/subscriptions/{sub_id}/edit")
    assert edit_page.status_code == 404

    edit_attempt = client.post(f"/subscriptions/{sub_id}/edit", data={
        "label": "Hijacked!", "keywords": "", "journals": "", "authors": "",
        "query_override": "", "recipient_email": "bob@example.com", "frequency": "weekly",
    })
    assert edit_attempt.status_code == 404

    # 数据库里那条订阅应该完全没被动过 / the subscription in the database is untouched
    untouched = db_session.get(Subscription, sub_id)
    assert untouched.label != "Hijacked!"


def test_user_cannot_delete_someone_elses_subscription(client, db_session):
    register_and_login(client, db_session, "alice", "alice@example.com")
    _create_subscription(client)

    from app.db import Subscription
    sub_id = db_session.query(Subscription).first().id

    register_and_login(client, db_session, "bob", "bob@example.com")
    response = client.post(f"/subscriptions/{sub_id}/delete")
    assert response.status_code == 404

    # 还在数据库里 / still exists in the database
    assert db_session.get(Subscription, sub_id) is not None


def test_user_cannot_view_someone_elses_articles(client, db_session):
    register_and_login(client, db_session, "alice", "alice@example.com")
    _create_subscription(client)

    from app.db import Subscription, SeenArticle
    sub_id = db_session.query(Subscription).first().id
    article = SeenArticle(subscription_id=sub_id, pmid="12345", title="Secret paper")
    db_session.add(article)
    db_session.commit()

    register_and_login(client, db_session, "bob", "bob@example.com")

    # B 不能看这个订阅的文献列表 / B can't view this subscription's article list
    preview = client.get(f"/subscriptions/{sub_id}/preview")
    assert preview.status_code == 404

    # B 也不能把这篇文章加进自己的待阅读清单 / B can't save this article to their own reading list
    save_attempt = client.post(f"/articles/{article.id}/save")
    assert save_attempt.status_code == 404
    assert db_session.get(SeenArticle, article.id).saved_for_reading is False


def test_two_users_have_independent_sender_settings(client, db_session):
    """A 改自己的发件邮箱，不应该影响到 B 的。
    A changing their own sender email shouldn't affect B's.
    """
    register_and_login(client, db_session, "alice", "alice@example.com")
    client.post("/settings", data={
        "smtp_host": "smtp.gmail.com", "smtp_port": "587", "smtp_use_ssl": "",
        "sender_email": "alice@gmail.com", "sender_password": "alicepass", "ncbi_api_key": "",
    })

    register_and_login(client, db_session, "bob", "bob@example.com")
    client.post("/settings", data={
        "smtp_host": "smtp.qq.com", "smtp_port": "465", "smtp_use_ssl": "1",
        "sender_email": "bob@qq.com", "sender_password": "bobpass", "ncbi_api_key": "",
    })

    from app.db import AppSettings, User
    alice_id = db_session.query(User).filter_by(username="alice").first().id
    bob_id = db_session.query(User).filter_by(username="bob").first().id
    alice_settings = db_session.query(AppSettings).filter_by(user_id=alice_id).first()
    bob_settings = db_session.query(AppSettings).filter_by(user_id=bob_id).first()

    assert alice_settings.sender_email == "alice@gmail.com"
    assert bob_settings.sender_email == "bob@qq.com"
