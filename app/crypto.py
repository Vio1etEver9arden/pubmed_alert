"""对存进数据库的敏感字段（如 Gmail 应用密码）做对称加密；也管邮件里"勾选加入待阅读"链接用的
签名 token。
Symmetric encryption for sensitive fields stored in the DB (e.g. the Gmail app password); also
handles the signed tokens used by the "select articles for your reading list" email links.
"""
import hashlib
import hmac

from cryptography.fernet import Fernet

from app.config import APP_SECRET_KEY

_fernet = Fernet(APP_SECRET_KEY)

# 派生出一个专用密钥，不直接拿 APP_SECRET_KEY 原始值当 HMAC 密钥——简单的一次性密钥分离，
# 成本几乎为零。Derive a purpose-specific key rather than using APP_SECRET_KEY's raw bytes
# directly as the HMAC key — cheap one-step key separation.
_READING_LIST_KEY = hmac.new(APP_SECRET_KEY, b"reading-list-token", hashlib.sha256).digest()


def encrypt(value: str) -> str:
    if not value:
        return ""
    return _fernet.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    if not value:
        return ""
    return _fernet.decrypt(value.encode()).decode()


def _reading_list_message(user_id, article_ids) -> bytes:
    ids_str = ",".join(str(i) for i in sorted(article_ids))
    return f"pick-reading:{user_id}:{ids_str}".encode()


def make_reading_list_token(user_id, article_ids) -> str:
    return hmac.new(_READING_LIST_KEY, _reading_list_message(user_id, article_ids), hashlib.sha256).hexdigest()


def verify_reading_list_token(user_id, article_ids, token: str) -> bool:
    expected = make_reading_list_token(user_id, article_ids)
    return hmac.compare_digest(expected, (token or ""))
