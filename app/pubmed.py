"""
NCBI E-utilities 客户端：构造检索式、查询新文献、抓取文献详情。
NCBI E-utilities client: build search queries, look up new articles, fetch article details.

官方文档 / Official docs: https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""
import time
import xml.etree.ElementTree as ET

import requests

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _params(extra, api_key=None):
    p = dict(extra)
    if api_key:
        p["api_key"] = api_key
    return p


def build_query(keywords=None, journals=None, authors=None, query_override=None):
    """把 关键词/期刊/作者 拼成 PubMed 检索式；同类内部 OR，跨类别 AND。
    Combine keywords/journals/authors into a PubMed query: OR within a category, AND across categories.
    如果提供了 query_override，直接原样使用（供高级用户手写检索式）。
    If query_override is given, it's used verbatim (for advanced users writing raw queries).
    """
    if query_override and query_override.strip():
        return query_override.strip()

    groups = []
    if keywords:
        terms = " OR ".join(f'"{kw}"[Title/Abstract]' for kw in keywords if kw.strip())
        if terms:
            groups.append(f"({terms})")
    if journals:
        terms = " OR ".join(f'"{j}"[Journal]' for j in journals if j.strip())
        if terms:
            groups.append(f"({terms})")
    if authors:
        terms = " OR ".join(f'"{a}"[Author]' for a in authors if a.strip())
        if terms:
            groups.append(f"({terms})")

    return " AND ".join(groups)


def search_pmids(query, retmax=100, api_key=None, sort="date", reldate_days=None):
    """查询 PMID 列表。sort="date" 按发表日期降序（默认，用于日常增量轮询）；
    sort="relevance" 按相关度排序（用于订阅刚建立时的一次性回溯）。
    reldate_days 限定只搜索最近 N 天内发表的文献。
    Look up PMIDs. sort="date" = newest first (default, for day-to-day incremental polling);
    sort="relevance" = most relevant first (for the one-off backfill when a subscription is created).
    reldate_days restricts the search to articles published within the last N days.
    """
    if not query:
        return []
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": retmax,
        "sort": sort,
        "retmode": "json",
    }
    if reldate_days:
        params["reldate"] = reldate_days
        params["datetype"] = "pdat"
    resp = requests.get(
        f"{EUTILS_BASE}/esearch.fcgi",
        params=_params(params, api_key=api_key),
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("esearchresult", {}).get("idlist", [])


def _text(el):
    return "".join(el.itertext()).strip() if el is not None else ""


def fetch_details(pmids, api_key=None):
    """批量抓取文献详情（标题/作者/期刊/ISSN/摘要/DOI/发表日期）
    Batch-fetch article details (title/authors/journal/ISSN/abstract/DOI/pub date)
    """
    if not pmids:
        return []

    results = []
    # NCBI 建议一次不要请求过多 id，这里按 200 一批分页 / NCBI recommends chunking large id lists
    chunk_size = 200
    for i in range(0, len(pmids), chunk_size):
        chunk = pmids[i:i + chunk_size]
        resp = requests.get(
            f"{EUTILS_BASE}/efetch.fcgi",
            params=_params({
                "db": "pubmed",
                "id": ",".join(chunk),
                "rettype": "abstract",
                "retmode": "xml",
            }, api_key=api_key),
            timeout=30,
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        for article in root.findall(".//PubmedArticle"):
            medline = article.find("./MedlineCitation")
            pmid = _text(medline.find("./PMID"))
            article_el = medline.find("./Article")

            title = _text(article_el.find("./ArticleTitle"))

            abstract_parts = [
                _text(t) for t in article_el.findall("./Abstract/AbstractText")
            ]
            abstract = " ".join(p for p in abstract_parts if p)

            journal_title = _text(article_el.find("./Journal/Title"))
            issn = _text(article_el.find("./Journal/ISSN"))

            authors = []
            for a in article_el.findall("./AuthorList/Author"):
                last = _text(a.find("./LastName"))
                initials = _text(a.find("./Initials"))
                collective = _text(a.find("./CollectiveName"))
                if last:
                    authors.append(f"{last} {initials}".strip())
                elif collective:
                    authors.append(collective)

            year = _text(article_el.find("./Journal/JournalIssue/PubDate/Year"))
            medline_date = _text(article_el.find("./Journal/JournalIssue/PubDate/MedlineDate"))
            pub_date = year or medline_date or ""

            doi = ""
            for aid in article.findall("./PubmedData/ArticleIdList/ArticleId"):
                if aid.get("IdType") == "doi":
                    doi = _text(aid)

            results.append({
                "pmid": pmid,
                "title": title,
                "authors": ", ".join(authors),
                "journal": journal_title,
                "issn": issn,
                "pub_date": pub_date,
                "doi": doi,
                "abstract": abstract,
            })

        time.sleep(0.34 if not api_key else 0.11)  # 粗略限速，遵守 NCBI 速率建议 / rough rate limiting per NCBI guidance

    return results


def find_new_articles(keywords=None, journals=None, authors=None, query_override=None,
                       retmax=100, api_key=None, sort="date", reldate_days=None):
    """便捷函数：构造检索式 -> 查PMID -> 抓详情，一步到位
    Convenience wrapper: build query -> search PMIDs -> fetch details, all in one call
    """
    query = build_query(keywords, journals, authors, query_override)
    pmids = search_pmids(query, retmax=retmax, api_key=api_key, sort=sort, reldate_days=reldate_days)
    return query, fetch_details(pmids, api_key=api_key)
