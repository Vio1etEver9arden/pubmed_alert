"""
把文献列表导出成 RIS 格式，方便导入 EndNote / Zotero / Mendeley 这类文献管理软件。
Exports a list of articles as RIS, for import into reference managers (EndNote / Zotero /
Mendeley, etc.).

格式说明 / Format reference: https://en.wikipedia.org/wiki/RIS_(file_format)
"""


def build_ris(articles) -> str:
    lines = []
    for a in articles:
        lines.append("TY  - JOUR")
        if a.title:
            lines.append(f"TI  - {a.title}")
        for author in (a.authors or "").split(", "):
            author = author.strip()
            if author:
                lines.append(f"AU  - {author}")
        if a.journal:
            lines.append(f"JO  - {a.journal}")
        if a.pub_date:
            lines.append(f"PY  - {a.pub_date}")
        if a.doi:
            lines.append(f"DO  - {a.doi}")
        if a.abstract:
            lines.append(f"AB  - {a.abstract}")
        lines.append(f"UR  - {a.pubmed_url}")
        lines.append("ER  - ")
        lines.append("")
    return "\n".join(lines)
