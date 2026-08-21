"""
查 Unpaywall API，看某篇文章有没有免费的开放获取全文 PDF。

Unpaywall 免费、不需要注册账号，但按官方要求，每次请求都要带一个联系邮箱（只在滥用/出问题
时用来联系你，不会做其他用途）——这里直接复用 .env 里配置的系统发件邮箱；没配置的话就直接
跳过查询，不强求用户为了这一个小功能单独再配一个邮箱。

Query the Unpaywall API for a free, open-access full-text PDF for a given article.

Unpaywall is free and needs no account, but per their terms every request must include a
contact email (used only to reach you in case of abuse — nothing else). This reuses the system
sender email already configured in .env; if that isn't set, lookups are skipped outright rather
than forcing the user to configure a separate email just for this one small feature.

官方文档 / Official docs: https://unpaywall.org/products/api
"""
import requests

from app import config

UNPAYWALL_BASE = "https://api.unpaywall.org/v2"


def lookup(doi):
    """给一个 DOI，返回开放获取全文 PDF 的链接；查不到 / 没有 DOI / 没配置联系邮箱 / 请求失败
    都返回 None（不抛异常，调用方不需要额外做异常处理）。

    Given a DOI, return an open-access full-text PDF URL. Returns None if there's no DOI, no
    contact email configured, no OA copy found, or the request fails — never raises, so callers
    don't need extra error handling.
    """
    if not doi or not config.SYSTEM_SENDER_EMAIL:
        return None
    try:
        resp = requests.get(
            f"{UNPAYWALL_BASE}/{doi}",
            params={"email": config.SYSTEM_SENDER_EMAIL},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
    except requests.RequestException:
        return None

    best = data.get("best_oa_location") or {}
    return best.get("url_for_pdf") or best.get("url") or None
