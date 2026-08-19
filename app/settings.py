"""每个用户各自的设置行的读取/初始化逻辑。
Read/initialize each user's own settings row.
"""
from app.db import AppSettings


def get_settings(session, user_id: int) -> AppSettings:
    row = session.query(AppSettings).filter_by(user_id=user_id).first()
    if row is not None:
        return row

    row = AppSettings(user_id=user_id)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
