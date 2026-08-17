"""全局设置的读取/初始化逻辑。首次运行时如果检测到旧版 .env 里配置过 Gmail，会自动迁移过来一次。
Read/initialize the singleton settings row. On first run, if the old .env-based Gmail config is
detected, it's migrated over automatically (one-time).
"""
from app.db import AppSettings
from app.config import (
    LEGACY_GMAIL_ADDRESS, LEGACY_GMAIL_APP_PASSWORD,
    LEGACY_NCBI_API_KEY, LEGACY_POLL_INTERVAL_HOURS,
)

SETTINGS_ID = 1


def get_settings(session) -> AppSettings:
    row = session.get(AppSettings, SETTINGS_ID)
    if row is not None:
        return row

    row = AppSettings(
        id=SETTINGS_ID,
        sender_email=LEGACY_GMAIL_ADDRESS,
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_use_ssl=False,
        ncbi_api_key=LEGACY_NCBI_API_KEY,
        poll_interval_hours=float(LEGACY_POLL_INTERVAL_HOURS) if LEGACY_POLL_INTERVAL_HOURS else 6.0,
    )
    if LEGACY_GMAIL_APP_PASSWORD:
        row.sender_password = LEGACY_GMAIL_APP_PASSWORD
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
