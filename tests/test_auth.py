"""
测试 app/auth.py 里那些"纯逻辑"的函数——不需要数据库、不需要网络，输入什么、该输出什么，
直接断言就行。这类测试是最简单、最容易看懂的一种：每个函数就是"给定这样的输入 -> 应该得到
那样的输出"。

Tests for the "pure logic" functions in app/auth.py — no database, no network needed; given
this input, assert we get that output. This is the simplest, easiest-to-read kind of test:
each one is just "feed it this input -> expect that output".
"""
from app.auth import (
    hash_password,
    verify_password,
    verify_invite_code,
    is_valid_username,
    generate_code,
    hash_code,
    verify_code,
)


def test_hash_password_is_not_the_plain_password():
    """密码哈希之后，存起来的字符串里不应该直接看到原始密码。
    After hashing, the stored string shouldn't contain the raw password anywhere in it.
    """
    hashed = hash_password("mySecret123")
    assert "mySecret123" not in hashed
    assert hashed.startswith("scrypt$")


def test_verify_password_accepts_the_right_password():
    hashed = hash_password("mySecret123")
    assert verify_password("mySecret123", hashed) is True


def test_verify_password_rejects_the_wrong_password():
    hashed = hash_password("mySecret123")
    assert verify_password("wrongGuess", hashed) is False


def test_hashing_the_same_password_twice_gives_different_results():
    """两次哈希同一个密码，结果应该不一样——因为每次都会加一段随机的"盐"。
    如果这个测试失败了，说明"盐"没有生效，是个安全问题。
    Hashing the same password twice should give different results, because a random "salt" is
    mixed in each time. If this test ever fails, the salt isn't working — that's a security bug.
    """
    assert hash_password("mySecret123") != hash_password("mySecret123")


def test_verify_invite_code_accepts_the_configured_code():
    # tests/conftest.py 把邀请码设成了 "test-invite-code"
    # tests/conftest.py set the invite code to "test-invite-code"
    assert verify_invite_code("test-invite-code") is True


def test_verify_invite_code_rejects_wrong_code():
    assert verify_invite_code("wrong-code") is False


def test_verify_invite_code_trims_whitespace():
    """用户复制粘贴邀请码时前后可能带空格，不应该因为这个就失败。
    Users might paste the invite code with extra whitespace — that shouldn't cause a false
    rejection.
    """
    assert verify_invite_code("  test-invite-code  ") is True


def test_username_format_rules():
    # 合法：字母开头，3-20位，只有字母/数字/下划线
    # Valid: starts with a letter, 3-20 chars, only letters/digits/underscores
    assert is_valid_username("alice") is True
    assert is_valid_username("Bob_123") is True
    # 不合法：太短、数字开头、带特殊符号
    # Invalid: too short, starts with a digit, has a special character
    assert is_valid_username("ab") is False
    assert is_valid_username("1bob") is False
    assert is_valid_username("bob!") is False
    assert is_valid_username("") is False


def test_verification_code_is_six_digits():
    code = generate_code()
    assert len(code) == 6
    assert code.isdigit()


def test_verify_code_round_trip():
    """生成一个验证码 -> 哈希它 -> 拿原始验证码去验证，应该能对上。
    Generate a code -> hash it -> verify with the original code — it should match.
    """
    code = generate_code()
    stored_hash = hash_code(code)
    assert verify_code(code, stored_hash) is True


def test_verify_code_rejects_wrong_code():
    code_hash = hash_code("123456")
    assert verify_code("000000", code_hash) is False
