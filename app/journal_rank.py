"""
按期刊查影响因子 (JIF) 和官方 JCR 分区。

数据来自 Clarivate Journal Citation Reports 的 PDF 报告，需要你自己有订阅权限，手动导出
PDF 后用 scripts/parse_jcr_pdf.py 解析成 data/jcr_cache.csv（每年更新一次）。

Looks up Journal Impact Factor (JIF) and the official JCR quartile for a journal.

Data comes from a Clarivate Journal Citation Reports PDF export — you need your own JCR
subscription access. Export the PDF yourself and run scripts/parse_jcr_pdf.py to turn it into
data/jcr_cache.csv (refresh once a year).
"""
import csv
import difflib
import re
import functools

from app.config import JCR_CSV_PATH

_ISSN_RE = re.compile(r"[^0-9Xx]")


def _normalize_issn(issn):
    if not issn:
        return ""
    return _ISSN_RE.sub("", issn).upper()


def _normalize_title(title):
    if not title:
        return ""
    t = title.lower().strip()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t)
    # 去掉常见的冠词，提高匹配率 / strip common leading articles to improve match rate
    t = re.sub(r"^(the|a|an) ", "", t)
    return t.strip()


@functools.lru_cache(maxsize=1)
def _load_index():
    """返回 (issn_index, title_index, title_keys_list)，若文件不存在返回 (None, None, None)
    Returns (issn_index, title_index, title_keys_list); (None, None, None) if the file is missing.
    """
    if not JCR_CSV_PATH.exists():
        return None, None, None

    issn_index = {}
    title_index = {}

    with open(JCR_CSV_PATH, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or "").strip()
            quartile = (row.get("quartile") or "").strip() or None
            jif = (row.get("jif2026") or "").lstrip("<").strip()

            record = {
                "name": name,
                "quartile": quartile if quartile and quartile != "N/A" else None,
                "jif": float(jif) if jif and jif != "N/A" else None,
            }

            norm_title = _normalize_title(name)
            if norm_title and norm_title not in title_index:
                title_index[norm_title] = record

            norm_issn = _normalize_issn(row.get("eissn"))
            if norm_issn:
                issn_index[norm_issn] = record

    return issn_index, title_index, list(title_index.keys())


_JIF_EMAIL_COLORS = {
    "jif-high": ("#fdecea", "#c0392b"),       # 红 red: IF > 10
    "jif-mid-high": ("#fff4e5", "#b9770e"),   # 橙 orange: 5 <= IF <= 10
    "jif-mid": ("#fef9e7", "#9a7d0a"),        # 黄 yellow: 3 <= IF < 5
    "jif-low": ("#eafaf1", "#1e8449"),        # 绿 green: IF < 3
}


def jif_badge_class(jif):
    """按影响因子数值分档，返回一个 CSS 类名后缀（网页上给 IF 徽章上色用）。
    IF>10 红、5-10 橙、3-5 黄、<3 绿；没有影响因子数据就返回空字符串。

    Buckets a JIF value into a CSS class suffix (used to color the IF badge on the web pages).
    IF>10 red, 5-10 orange, 3-5 yellow, <3 green; an empty string if there's no JIF data.
    """
    if jif is None:
        return ""
    if jif > 10:
        return "jif-high"
    if jif >= 5:
        return "jif-mid-high"
    if jif >= 3:
        return "jif-mid"
    return "jif-low"


def jif_badge_colors(jif):
    """跟 jif_badge_class() 分档规则一样，但直接返回 (背景色, 文字色) 的十六进制颜色——邮件模板
    要用，因为大多数邮件客户端不支持外部 CSS/`<style>` 里定义的 class，必须写成内联 style。

    Same bucketing as jif_badge_class(), but returns (background, text) hex colors directly —
    needed by the email template, since most email clients strip external CSS/`<style>` classes
    and require inline style attributes instead.
    """
    cls = jif_badge_class(jif)
    return _JIF_EMAIL_COLORS.get(cls, ("#eef6ff", "#0a5cd8"))


def is_available():
    """JCR 数据文件是否已经放好 / whether the JCR data file has been placed"""
    return JCR_CSV_PATH.exists()


def lookup(journal_title=None, issn=None, issn_linking=None):
    """依次尝试：NLM 稳定 ISSN -> 文章自带的 ISSN -> 标题精确/模糊匹配。
    Try in order: NLM's stable linking ISSN -> the article's own ISSN -> exact/fuzzy title match.

    文章自带的 ISSN 有时是印刷版有时是电子版（不同文章不一定一致），而这份 JCR 数据只有电子版
    ISSN，所以两个 ISSN 都试一遍，比只试一个命中率更高；都没中再退到标题匹配兜底。
    An article's own ISSN can be either print or electronic (inconsistently, across articles) —
    and this JCR data only has electronic ISSNs — so trying both candidates beats trying just one;
    title matching is the final fallback.
    """
    issn_index, title_index, title_keys = _load_index()
    if issn_index is None:
        return None

    for candidate in (issn_linking, issn):
        norm = _normalize_issn(candidate)
        if norm and norm in issn_index:
            return issn_index[norm]

    norm_title = _normalize_title(journal_title)
    if not norm_title:
        return None

    if norm_title in title_index:
        return title_index[norm_title]

    close = difflib.get_close_matches(norm_title, title_keys, n=1, cutoff=0.9)
    if close:
        return title_index[close[0]]

    return None
