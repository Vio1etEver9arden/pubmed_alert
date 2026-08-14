import os
from pathlib import Path
from dotenv import load_dotenv
from cryptography.fernet import Fernet

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

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

SJR_CSV_PATH = DATA_DIR / "sjr_cache.csv"
# Scimago 每年发布一次全量期刊数据，下载地址格式固定 / Scimago publishes a yearly full dump at this stable URL pattern
SJR_DOWNLOAD_URL = "https://www.scimagojr.com/journalrank.php?out=xls"

MAIL_FROM_NAME = "PubMed Alert"
