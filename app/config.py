import os
import secrets
import sys
from pathlib import Path
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# 打包成单文件 exe 后，sys.executable 指向 exe 本身（数据要写在它旁边才能持久保存），
# 而模板/静态文件等只读资源被解压到 sys._MEIPASS 指向的临时目录里。
# When frozen into a onefile exe, sys.executable points at the exe itself (data must live next
# to it to persist across runs), while read-only bundled resources (templates/static) are
# unpacked into the temp dir pointed to by sys._MEIPASS.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    RESOURCE_DIR = BASE_DIR

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

TEMPLATES_DIR = RESOURCE_DIR / "app" / "templates"
STATIC_DIR = RESOURCE_DIR / "app" / "static"

load_dotenv(BASE_DIR / ".env")

# 加密密钥：自动生成并保存在本地文件，用户不需要手动配置。
# Encryption key: auto-generated and saved to a local file — no manual setup required.
SECRET_KEY_PATH = DATA_DIR / "app_secret.key"


def _load_or_create_secret_key():
    if SECRET_KEY_PATH.exists():
        return SECRET_KEY_PATH.read_bytes().strip()
    key = Fernet.generate_key()
    SECRET_KEY_PATH.write_bytes(key)
    return key


APP_SECRET_KEY = _load_or_create_secret_key()

# 注册邀请码：部署到服务器给多人用时的额外一道保险——即使网络层配置失误暴露到公网，陌生人没有
# 这个码也注册不了账号。可以在 .env 里设 REGISTER_INVITE_CODE 自己定一个好记的；不设的话首次
# 启动自动生成一个随机码存在本地文件里，跟 app_secret.key 一样不需要手动配置。
# Registration invite code: an extra safety net for a multi-person server deployment — even if
# the network layer is accidentally misconfigured and exposed to the public internet, strangers
# can't register without this code. Set REGISTER_INVITE_CODE in .env to pick a memorable one;
# otherwise a random code is auto-generated on first run and saved locally, same as app_secret.key.
INVITE_CODE_PATH = DATA_DIR / "invite_code.txt"


def _load_or_create_invite_code():
    env_code = os.getenv("REGISTER_INVITE_CODE", "").strip()
    if env_code:
        return env_code
    if INVITE_CODE_PATH.exists():
        return INVITE_CODE_PATH.read_text().strip()
    code = secrets.token_urlsafe(9)
    INVITE_CODE_PATH.write_text(code)
    return code


REGISTER_INVITE_CODE = _load_or_create_invite_code()

# 系统级发件账号：给注册验证码/找回密码这类"系统邮件"用，跟每个用户自己在「设置」页配的发件
# 邮箱（给文献提醒用）是两码事——这时候用户可能还不存在，没法用他自己的配置。SMTP 凭证没法凭空
# 生成，所以这里不像邀请码那样自动造一个，不配置的话对应功能会报错提示。
# System-level sender account: used for "system" emails like registration/password-reset codes,
# distinct from each user's own sender email on the Settings page (which is for literature
# alerts) — at this point the user may not exist yet, so their own config can't be used. SMTP
# credentials can't be conjured out of nothing, so unlike the invite code this has no
# auto-generated fallback; the relevant features just error out with a clear message if unset.
SYSTEM_SENDER_EMAIL = os.getenv("SYSTEM_SENDER_EMAIL", "")
SYSTEM_SENDER_PASSWORD = os.getenv("SYSTEM_SENDER_PASSWORD", "")
SYSTEM_SMTP_HOST = os.getenv("SYSTEM_SMTP_HOST", "smtp.gmail.com")
SYSTEM_SMTP_PORT = int(os.getenv("SYSTEM_SMTP_PORT", "587"))
SYSTEM_SMTP_USE_SSL = os.getenv("SYSTEM_SMTP_USE_SSL", "").strip().lower() in ("1", "true", "yes")

# 提醒邮件里"选择要加入待阅读的文献"链接需要一个外部可访问的完整地址——猜不出你的 Tailscale/
# 公网地址，所以不自动生成；但这只是锦上添花的功能，不配置的话邮件照常发送，只是没有这个链接，
# 不像系统发件账号那样是硬性要求。
# The "select articles to add to your reading list" link in alert emails needs a full externally
# reachable address — can't be auto-generated (no way to guess your Tailscale/public hostname).
# But this is a pure enhancement, not a hard requirement like the system sender account: unset,
# emails still send normally, just without that link.
APP_BASE_URL = os.getenv("APP_BASE_URL", "").strip().rstrip("/")

DB_PATH = DATA_DIR / "subscriptions.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# 仓库/打包自带的那份，开发者每年更新一次；不支持用户自己放一份覆盖。
# The copy shipped with the repo/package, refreshed once a year by the developer; there's no
# user-supplied override.
JCR_CSV_PATH = RESOURCE_DIR / "data" / "jcr_cache.csv"

MAIL_FROM_NAME = "PubMed Alert"
