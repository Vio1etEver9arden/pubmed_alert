"""
用 Scimago Journal Rank (SJR) 免费数据近似替代官方 JCR / 中科院分区。
Uses the free Scimago Journal Rank (SJR) dataset as an approximation for official JCR / CAS quartiles.

⚠️ 这不是官方 JCR 影响因子或中科院分区数据，仅供参考！
⚠️ This is NOT the official JCR impact factor or CAS partition data — for reference only!

Scimago 网站有 Cloudflare 人机验证，无法用程序自动下载，需要你手动下载 CSV 文件放到 data/sjr_cache.csv。
Scimago's site is behind Cloudflare bot-protection and can't be downloaded programmatically —
you need to manually download the CSV and place it at data/sjr_cache.csv. See README for steps.
"""
import csv
import difflib
import re
import functools

from app.config import SJR_CSV_PATH

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
    if not SJR_CSV_PATH.exists():
        return None, None, None

    issn_index = {}
    title_index = {}

    with open(SJR_CSV_PATH, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            title = row.get("Title", "").strip()
            quartile = row.get("SJR Best Quartile", "").strip() or None
            sjr = row.get("SJR", "").replace(",", ".").strip()
            rank_str = row.get("Rank", "").strip()

            record = {
                "title": title,
                "quartile": quartile if quartile and quartile != "-" else None,
                "sjr": float(sjr) if sjr and sjr != "-" else None,
                "rank": int(rank_str) if rank_str.isdigit() else None,
            }

            norm_title = _normalize_title(title)
            if norm_title and norm_title not in title_index:
                title_index[norm_title] = record

            issn_field = row.get("Issn", "") or row.get("ISSN", "")
            for raw_issn in issn_field.split(","):
                norm_issn = _normalize_issn(raw_issn)
                if norm_issn:
                    issn_index[norm_issn] = record

    return issn_index, title_index, list(title_index.keys())


def is_available():
    """SJR 数据文件是否已经放好 / whether the SJR data file has been placed"""
    return SJR_CSV_PATH.exists()


def lookup(journal_title=None, issn=None):
    """按 ISSN 优先，其次按标题精确/模糊匹配期刊评级
    Try ISSN match first, then exact/fuzzy title match. Returns None if no data file or no match.
    """
    issn_index, title_index, title_keys = _load_index()
    if issn_index is None:
        return None

    norm_issn = _normalize_issn(issn)
    if norm_issn and norm_issn in issn_index:
        return issn_index[norm_issn]

    norm_title = _normalize_title(journal_title)
    if not norm_title:
        return None

    if norm_title in title_index:
        return title_index[norm_title]

    close = difflib.get_close_matches(norm_title, title_keys, n=1, cutoff=0.9)
    if close:
        return title_index[close[0]]

    return None
