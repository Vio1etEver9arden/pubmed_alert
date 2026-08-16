"""
用 Gmail SMTP + 应用专用密码发送邮件。凭证来自网页「设置」页面保存的 AppSettings（密码加密存储）。
Sends email via Gmail SMTP with an App Password. Credentials come from the AppSettings row saved
via the web "Settings" page (the password is stored encrypted).
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import MAIL_FROM_NAME, TEMPLATES_DIR

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def is_configured(settings):
    return bool(settings.gmail_address and settings.gmail_app_password)


def render_digest_html(subscription, articles):
    template = _env.get_template("email_digest.html")
    return template.render(subscription=subscription, articles=articles)


def _send(settings, to_email, subject, html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{MAIL_FROM_NAME} <{settings.gmail_address}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.starttls()
        server.login(settings.gmail_address, settings.gmail_app_password)
        server.sendmail(settings.gmail_address, [to_email], msg.as_string())


def send_digest(settings, subscription, articles):
    """发送一封汇总邮件；未配置 Gmail 凭证时抛出异常，调用方需要提前用 is_configured() 检查
    Sends one digest email; raises if Gmail credentials aren't configured — callers should
    check is_configured() first.
    """
    if not is_configured(settings):
        raise RuntimeError("Gmail 尚未在「设置」页面配置 (Gmail not configured on the Settings page)")

    html = render_digest_html(subscription, articles)
    subject = f"[PubMed Alert] {subscription.label} - {len(articles)} 篇新文献 new article(s)"
    _send(settings, subscription.recipient_email, subject, html)


def send_test_email(settings, to_email):
    """在「设置」页面点击"发送测试邮件"时调用，用于验证 Gmail 配置是否正确
    Called from the "send test email" button on the Settings page, to verify Gmail config works.
    """
    if not is_configured(settings):
        raise RuntimeError("Gmail 尚未在「设置」页面配置 (Gmail not configured on the Settings page)")

    html = (
        "<p>✅ 这是一封来自 PubMed Alert 的测试邮件，如果你收到了它，说明 Gmail 配置正确。</p>"
        "<p>✅ This is a test email from PubMed Alert — if you received it, your Gmail setup is working.</p>"
    )
    _send(settings, to_email, "[PubMed Alert] 测试邮件 Test Email", html)
