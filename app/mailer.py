"""
用通用 SMTP（Gmail / QQ邮箱 / 163邮箱 / Outlook 或任意其他邮箱服务商）发送邮件。凭证来自网页
「设置」页面保存的 AppSettings（密码加密存储）。
Sends email via generic SMTP (Gmail / QQ Mail / 163 Mail / Outlook, or any other provider).
Credentials come from the AppSettings row saved via the web "Settings" page (the password is
stored encrypted).
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import config, crypto, journal_rank
from app.config import MAIL_FROM_NAME, TEMPLATES_DIR
from app.i18n import get_translator

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)
_env.globals["jif_badge_colors"] = journal_rank.jif_badge_colors

# 一封邮件里最多完整展示这么多篇文章。Gmail 等邮箱客户端对邮件正文大小有硬性限制（Gmail 大约
# 102KB，超过会被"裁剪"，只显示前面一部分，后面全部看不到，还会有个"查看完整邮件"的提示）——
# 加了 AI 总结/关键词/翻译标题这些内容之后，每篇文章占的篇幅比以前大不少，二三十篇往上就有实际
# 撞到这个上限的风险。超过这个数量的文章仍然会正常存进数据库、标记为已发送，只是邮件正文里不再
# 一篇篇展示，改成一句"还有 N 篇未显示，点这里查看完整列表"。
# Caps how many articles are fully rendered in one email. Email clients like Gmail enforce a hard
# size limit on the message body (Gmail's is roughly 102KB) — messages over that get "clipped",
# showing only the beginning with a "View entire message" link. With AI summaries/keywords/
# translated titles now included, each article takes up noticeably more space than before, so
# anything above roughly 20-30 articles risks actually hitting that limit. Articles beyond this
# cap are still stored and marked as sent normally — they just aren't individually rendered in the
# email body, replaced with a "N more not shown, view the full list" note instead.
EMAIL_MAX_ARTICLES = 20


def is_configured(settings):
    return bool(settings.smtp_host and settings.sender_email and settings.sender_password)


def target_langs(ui_language: str) -> list:
    """界面语言是英文就只用英文；中文/日文就是"英文+对应语言"两种都要。
    English UI language means English-only; Chinese/Japanese means both English and that
    language.
    """
    return ["en"] if ui_language == "en" else ["en", ui_language]


def _make_email_translator(ui_language: str):
    """返回一个 email_t(key) 函数，给邮件模板用：界面语言是英文就只输出英文文案，中文/日文就把
    英文和对应语言的文案用" · "拼在一起——这样同一套邮件模板既能发纯英文邮件，也能发双语邮件，
    不用为两种情况各写一份模板。
    Returns an email_t(key) function for email templates: English UI language means English-only
    text; Chinese/Japanese means the English and matching-language text joined with " · " — so
    the same email template produces either an English-only or a bilingual email without needing
    two separate template files.
    """
    translators = [get_translator(lang) for lang in target_langs(ui_language)]

    def email_t(key: str, **kwargs) -> str:
        parts = []
        for tr in translators:
            text = tr(key)
            if kwargs:
                text = text.format(**kwargs)
            if text not in parts:
                parts.append(text)
        return " · ".join(parts)

    return email_t


def render_digest_html(subscription, articles, ui_language="en"):
    """有配置 APP_BASE_URL 的话，额外算一个"选择要加入待阅读的文献"链接（一封邮件一个链接，
    带上这封邮件里所有文章的 id，不是每篇文章单独一个链接）；没配置就是 None，模板里不显示。
    If APP_BASE_URL is configured, also builds one "select articles for your reading list" link
    per email (covering every article in this digest, not one link per article); otherwise None
    and the template simply omits it.
    """
    template = _env.get_template("email_digest.html")
    pick_url = None
    if config.APP_BASE_URL and articles:
        article_ids = [a.id for a in articles]
        token = crypto.make_reading_list_token(subscription.user_id, article_ids)
        ids_str = ",".join(str(i) for i in article_ids)
        pick_url = f"{config.APP_BASE_URL}/reading-list/pick?u={subscription.user_id}&ids={ids_str}&t={token}"

    shown_articles = articles[:EMAIL_MAX_ARTICLES]
    hidden_count = len(articles) - len(shown_articles)
    view_all_url = None
    if hidden_count and config.APP_BASE_URL:
        view_all_url = f"{config.APP_BASE_URL}/subscriptions/{subscription.id}/preview"

    email_t = _make_email_translator(ui_language)
    return template.render(
        subscription=subscription, articles=shown_articles, hidden_count=hidden_count,
        view_all_url=view_all_url, reading_list_pick_url=pick_url, t=email_t,
    )


def _send(settings, to_email, subject, html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{MAIL_FROM_NAME} <{settings.sender_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html", "utf-8"))

    port = settings.smtp_port or 587
    if settings.smtp_use_ssl:
        server = smtplib.SMTP_SSL(settings.smtp_host, port, timeout=30)
    else:
        server = smtplib.SMTP(settings.smtp_host, port, timeout=30)
        server.starttls()
    try:
        server.login(settings.sender_email, settings.sender_password)
        server.sendmail(settings.sender_email, [to_email], msg.as_string())
    finally:
        server.quit()


def send_digest(settings, subscription, articles):
    """发送一封汇总邮件；未配置发件邮箱时抛出异常，调用方需要提前用 is_configured() 检查。
    邮件是纯英文还是英文+界面语言双语，由 settings.ui_language 决定（见 target_langs()）。
    Sends one digest email; raises if the sender account isn't configured — callers should
    check is_configured() first. Whether the email is English-only or bilingual (English + UI
    language) is determined by settings.ui_language (see target_langs()).
    """
    if not is_configured(settings):
        raise RuntimeError("发件邮箱尚未在「设置」页面配置 (Sender account not configured on the Settings page)")

    ui_language = getattr(settings, "ui_language", "en") or "en"
    html = render_digest_html(subscription, articles, ui_language)
    email_t = _make_email_translator(ui_language)
    subject = f"[PubMed Alert] {subscription.label} - " + email_t("email_subject_suffix", n=len(articles))
    _send(settings, subscription.recipient_email, subject, html)


def render_trend_digest_html(subscription, articles, prose, ui_language="en"):
    template = _env.get_template("email_trend_digest.html")
    email_t = _make_email_translator(ui_language)
    return template.render(subscription=subscription, articles=articles, prose=prose, t=email_t)


def send_trend_digest(settings, subscription, articles, prose):
    """发送每月一次的"趋势总结"邮件；prose 是 app.ai.write_trend_digest() 返回的
    {"prose_en": ..., "prose_local": ...}（后者纯英文界面下不存在）。
    Sends the once-a-month "trend digest" email; prose is the {"prose_en": ..., "prose_local":
    ...} dict returned by app.ai.write_trend_digest() (the latter key absent for an English UI).
    """
    if not is_configured(settings):
        raise RuntimeError("发件邮箱尚未在「设置」页面配置 (Sender account not configured on the Settings page)")

    ui_language = getattr(settings, "ui_language", "en") or "en"
    html = render_trend_digest_html(subscription, articles, prose, ui_language)
    email_t = _make_email_translator(ui_language)
    subject = f"[PubMed Alert] {subscription.label} - " + email_t("email_trend_subject")
    _send(settings, subscription.recipient_email, subject, html)


def send_test_email(settings, to_email):
    """在「设置」页面点击"发送测试邮件"时调用，用于验证发件邮箱配置是否正确
    Called from the "send test email" button on the Settings page, to verify the sender
    account config works.
    """
    if not is_configured(settings):
        raise RuntimeError("发件邮箱尚未在「设置」页面配置 (Sender account not configured on the Settings page)")

    html = (
        "<p>✅ 这是一封来自 PubMed Alert 的测试邮件，如果你收到了它，说明发件邮箱配置正确。</p>"
        "<p>✅ This is a test email from PubMed Alert — if you received it, your sender account setup is working.</p>"
    )
    _send(settings, to_email, "[PubMed Alert] 测试邮件 Test Email", html)


def _system_settings():
    return SimpleNamespace(
        smtp_host=config.SYSTEM_SMTP_HOST,
        smtp_port=config.SYSTEM_SMTP_PORT,
        smtp_use_ssl=config.SYSTEM_SMTP_USE_SSL,
        sender_email=config.SYSTEM_SENDER_EMAIL,
        sender_password=config.SYSTEM_SENDER_PASSWORD,
    )


def is_system_mailer_configured():
    return is_configured(_system_settings())


def send_verification_email(to_email, code, purpose):
    """purpose: "register"（注册验证） 或 "reset"（找回密码）。
    用系统级发件账号发送，跟每个用户自己的发件邮箱配置无关——调用方需要提前用
    is_system_mailer_configured() 检查。
    purpose: "register" or "reset". Sent via the system-level sender account, independent of any
    user's own sender settings — callers should check is_system_mailer_configured() first.
    """
    if not is_system_mailer_configured():
        raise RuntimeError(
            "系统发件账号尚未在 .env 里配置 (system sender account not configured in .env)"
        )

    if purpose == "reset":
        subject = "[PubMed Alert] 找回密码验证码 Password reset code"
        intro = (
            "<p>你正在找回 PubMed Alert 账号的密码，验证码是：</p>"
            "<p>You're resetting your PubMed Alert account password. Your code is:</p>"
        )
    else:
        subject = "[PubMed Alert] 注册验证码 Registration verification code"
        intro = (
            "<p>你正在注册 PubMed Alert 账号，验证码是：</p>"
            "<p>You're registering a PubMed Alert account. Your code is:</p>"
        )

    html = (
        f"{intro}"
        f"<p style=\"font-size:28px;font-weight:700;letter-spacing:4px;\">{code}</p>"
        "<p>10 分钟内有效，请勿泄露给他人。10 minutes validity — don't share this with anyone.</p>"
    )
    _send(_system_settings(), to_email, subject, html)
