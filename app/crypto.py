"""对存进数据库的敏感字段（如 Gmail 应用密码）做对称加密。
Symmetric encryption for sensitive fields stored in the DB (e.g. the Gmail app password).
"""
from cryptography.fernet import Fernet

from app.config import APP_SECRET_KEY

_fernet = Fernet(APP_SECRET_KEY)


def encrypt(value: str) -> str:
    if not value:
        return ""
    return _fernet.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    if not value:
        return ""
    return _fernet.decrypt(value.encode()).decode()
