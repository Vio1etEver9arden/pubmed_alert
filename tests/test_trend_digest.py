"""
测试月度趋势总结相关的纯逻辑：多久算"到期"（app/scheduler.py 的 is_trend_due），以及邮件该用
纯英文还是英文+界面语言双语（app/mailer.py 的 target_langs）。这两个都是不碰数据库/网络的纯
函数，直接断言输入输出就行。

Tests the pure logic behind the monthly trend digest: when a subscription is "due"
(app/scheduler.py's is_trend_due), and whether an email should be English-only or bilingual
(app/mailer.py's target_langs). Both are pure functions with no database/network involved.
"""
import datetime as dt
from types import SimpleNamespace

from app.scheduler import is_trend_due
from app.mailer import target_langs


def test_trend_due_when_never_sent():
    sub = SimpleNamespace(last_trend_sent_at=None)
    assert is_trend_due(sub, dt.datetime.utcnow()) is True


def test_trend_not_due_shortly_after_sending():
    now = dt.datetime.utcnow()
    sub = SimpleNamespace(last_trend_sent_at=now - dt.timedelta(days=5))
    assert is_trend_due(sub, now) is False


def test_trend_due_after_27_days():
    now = dt.datetime.utcnow()
    sub = SimpleNamespace(last_trend_sent_at=now - dt.timedelta(days=28))
    assert is_trend_due(sub, now) is True


def test_trend_not_due_at_26_days():
    now = dt.datetime.utcnow()
    sub = SimpleNamespace(last_trend_sent_at=now - dt.timedelta(days=26))
    assert is_trend_due(sub, now) is False


def test_target_langs_english_only():
    assert target_langs("en") == ["en"]


def test_target_langs_bilingual_chinese():
    assert target_langs("zh") == ["en", "zh"]


def test_target_langs_bilingual_japanese():
    assert target_langs("ja") == ["en", "ja"]
