"""
测试关键词/期刊/作者的拆分逻辑（换行、英文逗号、中文逗号、顿号、分号都能拆）。
Tests for splitting keywords/journals/authors (newline, English comma, Chinese comma, 顿号,
semicolon should all work as separators).
"""
from app.main import _split_lines


def test_splits_on_newline():
    assert _split_lines("CRISPR\nbase editing") == ["CRISPR", "base editing"]


def test_splits_on_english_comma():
    assert _split_lines("CRISPR,base editing") == ["CRISPR", "base editing"]


def test_splits_on_chinese_comma_and_enumeration_comma():
    assert _split_lines("CRISPR，base editing、prime editing") == [
        "CRISPR", "base editing", "prime editing",
    ]


def test_splits_on_semicolon():
    assert _split_lines("Nature;Cell；Science") == ["Nature", "Cell", "Science"]


def test_ignores_empty_lines_and_extra_whitespace():
    assert _split_lines("  CRISPR  \n\n  \n base editing ") == ["CRISPR", "base editing"]


def test_empty_input_gives_empty_list():
    assert _split_lines("") == []
    assert _split_lines(None) == []
