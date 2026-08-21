"""
测试影响因子(JIF)按数值分档上色的规则：>10 红、5-10 橙、3-5 黄、<3 绿。
纯逻辑函数，输入一个数字，检查分到了哪一档。

Tests the JIF-value-to-color bucketing rule: >10 red, 5-10 orange, 3-5 yellow, <3 green.
A pure logic function — feed it a number, check which bucket it lands in.
"""
from app.journal_rank import jif_badge_class, jif_badge_colors


def test_above_ten_is_red():
    assert jif_badge_class(15.2) == "jif-high"
    assert jif_badge_class(10.1) == "jif-high"


def test_five_to_ten_inclusive_is_orange():
    assert jif_badge_class(10.0) == "jif-mid-high"
    assert jif_badge_class(7.5) == "jif-mid-high"
    assert jif_badge_class(5.0) == "jif-mid-high"


def test_three_to_five_is_yellow():
    assert jif_badge_class(4.9) == "jif-mid"
    assert jif_badge_class(3.0) == "jif-mid"


def test_below_three_is_green():
    assert jif_badge_class(2.99) == "jif-low"
    assert jif_badge_class(1.0) == "jif-low"
    assert jif_badge_class(0.0) == "jif-low"


def test_none_gives_empty_class():
    assert jif_badge_class(None) == ""


def test_email_colors_match_the_same_buckets():
    bg, fg = jif_badge_colors(12.0)
    assert (bg, fg) == ("#fdecea", "#c0392b")

    bg, fg = jif_badge_colors(1.5)
    assert (bg, fg) == ("#eafaf1", "#1e8449")
