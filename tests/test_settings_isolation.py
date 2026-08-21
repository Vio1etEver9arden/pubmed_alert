"""
回归测试一个真实 bug：「设置」页面的"发件邮箱"和"AI 功能"曾经是两个分开的 <form>，但都提交到
同一个 /settings 路由。浏览器提交表单时只会带上那个表单自己的字段——所以提交"发件邮箱"表单时,
AI 那些字段根本不在这次提交里，会被 FastAPI 的 Form(...) 默认值悄悄覆盖掉（清空）；反过来提交
"AI 功能"表单也会把发件邮箱清空。用户是在实际使用时发现这个问题的："保存了邮箱设置，AI 设置就
没了；保存了AI设置，邮箱设置也没了"。

修复方式是把两个表单分别提交到两个独立的路由（/settings 和 /settings/ai），各自只处理、只覆盖
自己那部分字段。这些测试确保这两个路由今后不会又被合并回一个、重新引入这个 bug。

Regression test for a real bug: the Settings page's "sender email" and "AI features" sections
used to be two separate <form> elements that both posted to the same /settings route. A browser
only submits the fields belonging to the form actually submitted — so submitting the "sender
email" form left the AI fields out of that request entirely, and FastAPI's Form(...) defaults
silently overwrote (cleared) them; submitting the "AI features" form did the same to the sender
email fields. The user found this while actually using the app: "saving the email settings wiped
the AI settings, and saving the AI settings wiped the email settings."

Fixed by giving each form its own dedicated route (/settings and /settings/ai), each touching
only its own fields. These tests make sure the two don't get merged back into one route later,
re-introducing the bug.
"""
from tests.conftest import register_and_login
from app.db import AppSettings


def test_saving_mailer_settings_does_not_clear_ai_settings(client, db_session):
    register_and_login(client, db_session, "alice", "alice@example.com")

    client.post("/settings/ai", data={
        "ai_backend": "openai_compatible", "ai_provider_preset": "deepseek",
        "ai_base_url": "https://api.deepseek.com", "ai_api_key": "sk-real-key",
        "ai_model": "deepseek-chat",
    })

    client.post("/settings", data={
        "smtp_host": "smtp.gmail.com", "smtp_port": "587", "smtp_use_ssl": "",
        "sender_email": "me@gmail.com", "sender_password": "app-password", "ncbi_api_key": "",
    })

    settings = db_session.query(AppSettings).first()
    assert settings.ai_backend == "openai_compatible"
    assert settings.ai_base_url == "https://api.deepseek.com"
    assert settings.ai_api_key == "sk-real-key"
    assert settings.ai_model == "deepseek-chat"
    # 顺便确认邮箱那次保存本身也生效了 also confirm the mailer save itself took effect
    assert settings.sender_email == "me@gmail.com"


def test_saving_ai_settings_does_not_clear_mailer_settings(client, db_session):
    register_and_login(client, db_session, "alice", "alice@example.com")

    client.post("/settings", data={
        "smtp_host": "smtp.gmail.com", "smtp_port": "587", "smtp_use_ssl": "",
        "sender_email": "me@gmail.com", "sender_password": "app-password", "ncbi_api_key": "",
    })

    client.post("/settings/ai", data={
        "ai_backend": "anthropic", "ai_provider_preset": "anthropic",
        "ai_base_url": "", "ai_api_key": "sk-ant-real-key", "ai_model": "claude-haiku-4-5",
    })

    settings = db_session.query(AppSettings).first()
    assert settings.smtp_host == "smtp.gmail.com"
    assert settings.sender_email == "me@gmail.com"
    assert settings.sender_password == "app-password"
    # 顺便确认 AI 那次保存本身也生效了 also confirm the AI save itself took effect
    assert settings.ai_api_key == "sk-ant-real-key"


def test_resaving_ai_settings_with_blank_key_keeps_existing_key(client, db_session):
    """"留空 = 不修改"这条规则也要继续适用于 AI Key。
    The "blank = leave unchanged" rule should still apply to the AI key too.
    """
    register_and_login(client, db_session, "alice", "alice@example.com")

    client.post("/settings/ai", data={
        "ai_backend": "anthropic", "ai_provider_preset": "anthropic",
        "ai_base_url": "", "ai_api_key": "sk-ant-original", "ai_model": "claude-haiku-4-5",
    })
    client.post("/settings/ai", data={
        "ai_backend": "anthropic", "ai_provider_preset": "anthropic",
        "ai_base_url": "", "ai_api_key": "", "ai_model": "claude-sonnet-5",
    })

    settings = db_session.query(AppSettings).first()
    assert settings.ai_api_key == "sk-ant-original"
    assert settings.ai_model == "claude-sonnet-5"
