import os
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

# 以下几项现在改为在网页「设置」页面配置，存进数据库（密码字段加密存储）。
# These are now configured on the web "Settings" page and stored in the DB (password field encrypted).
# 这里仅作为"老用户从 .env 升级"时的一次性迁移来源，正常使用不会再读取它们。
# Kept here only as a one-time migration source for users upgrading from the old .env-based setup;
# normal operation no longer reads these directly.
LEGACY_GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
LEGACY_GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
LEGACY_NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")
LEGACY_POLL_INTERVAL_HOURS = os.getenv("POLL_INTERVAL_HOURS", "")

DB_PATH = DATA_DIR / "subscriptions.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

JCR_CSV_PATH = DATA_DIR / "jcr_cache.csv"

MAIL_FROM_NAME = "PubMed Alert"
