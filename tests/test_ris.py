"""
测试 RIS 导出功能。build_ris() 是一个很典型的"纯函数"：给它一份文献列表，它就吐出一段文本，
不碰数据库、不碰网络——这种函数最好测，也最适合刚开始学 Python 的人读。

Tests for the RIS export feature. build_ris() is a classic "pure function": feed it a list of
articles, it hands back a block of text — no database, no network involved. This is the easiest
kind of function to test, and a good one to read if you're new to Python.
"""
from types import SimpleNamespace

from app.ris import build_ris


def _fake_article(**overrides):
    """造一个"看起来像"数据库里 SeenArticle 的假对象，只填测试需要的几个字段。
    Build a fake object that "looks like" a database SeenArticle row, with only the fields this
    test needs.
    """
    defaults = dict(
        title="CRISPR editing in cancer cells",
        authors="Smith J, Doe A",
        journal="Nature",
        pub_date="2026",
        doi="10.1000/example",
        abstract="An example abstract.",
        pubmed_url="https://pubmed.ncbi.nlm.nih.gov/12345/",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_build_ris_includes_the_title():
    text = build_ris([_fake_article()])
    assert "TI  - CRISPR editing in cancer cells" in text


def test_build_ris_splits_multiple_authors_into_separate_lines():
    """作者字段存的时候是 "Smith J, Doe A" 这样一整条字符串，导出时应该拆成两行 AU。
    The authors field is stored as one string like "Smith J, Doe A" — export should split it
    into two separate AU lines.
    """
    text = build_ris([_fake_article(authors="Smith J, Doe A")])
    assert "AU  - Smith J" in text
    assert "AU  - Doe A" in text


def test_build_ris_skips_empty_optional_fields():
    """没有 DOI 的文章，导出结果里就不应该出现 "DO  - " 这一行。
    An article with no DOI shouldn't produce a "DO  - " line at all.
    """
    text = build_ris([_fake_article(doi=None)])
    assert "DO  -" not in text


def test_build_ris_separates_multiple_articles():
    """两篇文章应该各自有一个 "ER  - " 结尾标记，一共出现两次。
    Two articles should each get their own "ER  - " end-of-record marker — two in total.
    """
    text = build_ris([_fake_article(), _fake_article(title="A second paper")])
    assert text.count("ER  - ") == 2
    assert "A second paper" in text
