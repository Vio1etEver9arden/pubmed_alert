"""
用户认证：密码哈希（Scrypt）、登录会话（cookie token）、注册邀请码校验、邮箱验证码（注册/找回
密码共用）。
User authentication: password hashing (Scrypt), login sessions (cookie tokens), registration
invite-code verification, and email verification codes (shared by registration and password reset).
"""
import datetime as dt
import hashlib
import hmac
import os
import re
import secrets

from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from fastapi import Depends, Request
from sqlalchemy import func

from app.config import REGISTER_INVITE_CODE
from app.db import Session as DBSession
from app.db import User, get_db

SESSION_COOKIE = "session_token"
SESSION_LIFETIME_DAYS = 365

VERIFICATION_CODE_TTL = dt.timedelta(minutes=10)
VERIFICATION_MAX_ATTEMPTS = 5
RESEND_COOLDOWN = dt.timedelta(seconds=60)

USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,19}$")

# Scrypt 参数：memory-hard，比 PBKDF2 更抗暴力破解；cryptography 包本来就是依赖，不用加新包。
# Scrypt params: memory-hard, more brute-force-resistant than PBKDF2; cryptography is already a
# dependency, so this adds no new package.
_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_KEY_LEN = 32


class NotAuthenticated(Exception):
    """当前请求没有有效的登录会话。Current request has no valid login session."""


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = Scrypt(salt=salt, length=_SCRYPT_KEY_LEN, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P).derive(
        password.encode()
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """自描述格式，参数都存在哈希字符串里，以后调整参数不用迁移旧数据。
    Self-describing format — parameters live in the hash string itself, so tuning them later
    doesn't require migrating existing rows.
    """
    try:
        algo, n, r, p, salt_hex, digest_hex = stored_hash.split("$")
        if algo != "scrypt":
            return False
        expected = bytes.fromhex(digest_hex)
        computed = Scrypt(
            salt=bytes.fromhex(salt_hex), length=len(expected), n=int(n), r=int(r), p=int(p)
        ).derive(password.encode())
        return hmac.compare_digest(computed, expected)
    except Exception:
        return False


def verify_invite_code(code: str) -> bool:
    return hmac.compare_digest((code or "").strip().encode(), REGISTER_INVITE_CODE.encode())


def is_valid_username(name: str) -> bool:
    return bool(USERNAME_RE.match(name or ""))


def find_user_by_identifier(db, identifier: str):
    """登录、找回密码都用这个：标识符可以是用户名（大小写不敏感）或邮箱。
    Used by both login and forgot-password: the identifier can be a username (case-insensitive)
    or an email address.
    """
    identifier = (identifier or "").strip()
    if not identifier:
        return None
    return db.query(User).filter(
        (func.lower(User.username) == identifier.lower()) | (User.email == identifier.lower())
    ).first()


def generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def verify_code(code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_code(code), code_hash)


def create_session(db, user: User) -> str:
    """创建一条登录会话，返回要写进 cookie 的原始 token（数据库里只存它的哈希）。
    Creates a login session, returning the raw token to store in the cookie (only its hash is
    kept in the DB).
    """
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = dt.datetime.utcnow() + dt.timedelta(days=SESSION_LIFETIME_DAYS)
    db.add(DBSession(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
    db.commit()
    return token


def delete_session(db, token: str):
    if not token:
        return
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    db.query(DBSession).filter_by(token_hash=token_hash).delete()
    db.commit()


def _lookup_user(db, token: str):
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    sess = db.query(DBSession).filter_by(token_hash=token_hash).first()
    if sess is None or sess.expires_at < dt.datetime.utcnow():
        return None
    return sess.user


def get_current_user(request: Request, db=Depends(get_db)) -> User:
    """强制要求登录的 FastAPI 依赖；未登录时抛 NotAuthenticated，由 main.py 里注册的异常处理器
    统一重定向到 /login。
    FastAPI dependency that requires login; raises NotAuthenticated when not logged in, caught by
    the exception handler registered in main.py to redirect to /login.
    """
    user = _lookup_user(db, request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise NotAuthenticated()
    return user


def get_current_user_optional(request: Request, db):
    """尽力而为、不抛异常的版本，给 base.html 显示"已登录: xxx / 退出登录"用。
    Best-effort, non-raising version — used to show "logged in as / logout" in base.html.
    """
    return _lookup_user(db, request.cookies.get(SESSION_COOKIE))
