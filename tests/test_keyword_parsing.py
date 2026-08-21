"""
测试关键词/期刊/作者的拆分逻辑：只按换行拆分，一行一个。

这里曾经短暂支持过用逗号/顿号/分号分隔，但很快就撤回了——因为期刊名字本身经常带逗号（比如
"Proceedings of the National Academy of Sciences, USA"），按逗号拆分会把这种期刊名从中间切开，
反而搜不到。所以这些测试里特意加了几个"逗号/顿号/分号不应该被当成分隔符"的例子，防止这个坑
将来又被不小心加回来。

Tests for splitting keywords/journals/authors: newline-only, one item per line.

This briefly also supported commas/enumeration commas/semicolons as separators, but that was
reverted almost immediately — some journal names legitimately contain a comma (e.g. "Proceedings
of the National Academy of Sciences, USA"), and splitting on comma would cut a name like that in
half, breaking the search. So these tests deliberately include a few "commas/enumeration
commas/semicolons must NOT act as separators" cases, to stop this pitfall from quietly creeping
back in.
"""
from app.main import _split_lines


def test_splits_on_newline():
    assert _split_lines("CRISPR\nbase editing") == ["CRISPR", "base editing"]


def test_does_not_split_on_english_comma():
    assert _split_lines("CRISPR,base editing") == ["CRISPR,base editing"]


def test_does_not_split_on_chinese_comma_or_enumeration_comma():
    assert _split_lines("CRISPR，base editing、prime editing") == [
        "CRISPR，base editing、prime editing",
    ]


def test_does_not_split_on_semicolon():
    assert _split_lines("Nature;Cell；Science") == ["Nature;Cell；Science"]


def test_journal_name_containing_a_comma_survives_intact():
    """这是撤回这个功能的直接原因：期刊名字本身带逗号，不应该被切开。
    This is the exact reason the feature was reverted: a journal name with a comma in it
    shouldn't get cut in half.
    """
    assert _split_lines("Proceedings of the National Academy of Sciences, USA") == [
        "Proceedings of the National Academy of Sciences, USA",
    ]


def test_ignores_empty_lines_and_extra_whitespace():
    assert _split_lines("  CRISPR  \n\n  \n base editing ") == ["CRISPR", "base editing"]


def test_empty_input_gives_empty_list():
    assert _split_lines("") == []
    assert _split_lines(None) == []
