"""
把 Journal Citation Reports 导出的 PDF 解析成 data/jcr_cache.csv，供 app/journal_rank.py 读取。

这个脚本不是应用运行时需要的依赖，只在你每年更新一次 JCR 数据时手动运行。需要你自己有 JCR
的订阅访问权限（一般通过所在机构的图书馆），导出年度报告 PDF 后本地解析，不涉及抓取或分发官方
付费数据。

用法 Usage:
    pip install pdfplumber
    python scripts/parse_jcr_pdf.py "data/JCR Journal Impact Factor 2026.pdf"

Parses a Journal Citation Reports PDF export into data/jcr_cache.csv, which app/journal_rank.py
reads at runtime.

This script isn't a runtime dependency of the app itself — run it manually whenever you refresh
your JCR data (about once a year). It requires your own JCR subscription access (typically via
your institution's library); export the annual report as a PDF and parse it locally. No scraping
or redistribution of the paywalled data is involved.
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("需要先安装 pdfplumber: pip install pdfplumber", file=sys.stderr)
    print("Install pdfplumber first: pip install pdfplumber", file=sys.stderr)
    sys.exit(1)

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "jcr_cache.csv"

TITLE_LINE = "Journal Citation Reports: Journal Impact Factor 2026"
HEADER_LINE = "Journal Name eISSN Index Citations JIF 2026 JIF 2025 JIF Quartile"

NUM = r"(?:<?\d+\.\d+|N/A)"
LINE_RE = re.compile(
    r"^(?P<name>.+?)\s*"
    r"(?P<eissn>\d{4}-\d{3}[\dXx]|N/A)\s*"
    r"(?P<index>[A-Z]{3,5}(?:,\s*[A-Z]{3,5})*)\s*"
    r"(?P<citations>\d+|N/A)\s*"
    rf"(?P<jif2026>{NUM})"
    rf"(?:\s*(?P<jif2025>{NUM}))?\s*"
    r"(?P<quartile>Q[1-4]|N/A)\s*$"
)

GAP_THRESHOLD = 3.0  # 相邻字符横向间隙超过这个值，就当作是两个不同的表格列（补一个空格）


def page_lines(page):
    """按原始内容流顺序重建每一行文字（而不是按坐标重新排序），列之间按横向间隙补空格。

    这份 PDF 里换行后的期刊名和 eISSN 列会在同一条 y 线上重叠，按坐标排序会把两段文字交错打乱
    （比如把 ISSN 和名字尾巴拆成一堆乱码字符）；而原始绘制顺序是正确的。同时相邻列之间常常没有
    真的空格字符，只是横向跳开一段距离，所以要按间隙人为补回空格——两个问题必须一起处理。

    Rebuild each line's text in original content-stream order (not re-sorted by coordinates),
    inserting a space wherever the horizontal gap between adjacent chars implies a new column.
    """
    groups = defaultdict(list)
    keys = []
    for c in page.chars:
        key = round(c["top"], 1)
        if key not in groups:
            keys.append(key)
        groups[key].append(c)
    for key in sorted(keys):
        parts = []
        prev_x1 = None
        for c in groups[key]:
            if prev_x1 is not None and (c["x0"] - prev_x1) > GAP_THRESHOLD:
                parts.append(" ")
            parts.append(c["text"])
            prev_x1 = c["x1"]
        yield "".join(parts)


def parse(pdf_path):
    rows = []
    unmatched = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            for line in page_lines(page):
                line = line.strip()
                if not line:
                    continue
                collapsed = line.replace(" ", "")
                if collapsed in (HEADER_LINE.replace(" ", ""), TITLE_LINE.replace(" ", "")):
                    continue
                m = LINE_RE.match(line)
                if m:
                    rows.append(m.groupdict())
                else:
                    unmatched.append((i + 1, line))
            if (i + 1) % 100 == 0:
                print(f"...{i+1}/{total} pages, {len(rows)} rows, {len(unmatched)} unmatched", file=sys.stderr)
    return rows, unmatched


def main():
    if len(sys.argv) < 2:
        print("用法 Usage: python scripts/parse_jcr_pdf.py <pdf路径> [输出csv路径]", file=sys.stderr)
        sys.exit(1)

    pdf_path = sys.argv[1]
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT

    rows, unmatched = parse(pdf_path)

    print(f"解析成功 parsed: {len(rows)} rows")
    if unmatched:
        print(f"解析失败 unmatched: {len(unmatched)} lines (前10条 first 10 shown)")
        for pg, line in unmatched[:10]:
            print(f"  [page {pg}] {line!r}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "eissn", "index", "citations", "jif2026", "jif2025", "quartile"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"已写入 wrote: {out_path}")


if __name__ == "__main__":
    main()
