"""
测试 app/unpaywall.py 的 lookup()。不会真的连网络——用 monkeypatch 把 requests.get 换成一个
假函数，让它返回我们编好的假数据，这样测试永远又快又稳定，不依赖 Unpaywall 服务器是否在线。

Tests for app/unpaywall.py's lookup(). No real network call — monkeypatch swaps out
requests.get with a fake that returns data we control, so the test is always fast and stable,
independent of whether the real Unpaywall service is up.
"""
from types import SimpleNamespace

from app import unpaywall


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self):
        return self._json_data


def test_returns_none_when_doi_is_missing():
    assert unpaywall.lookup(None) is None
    assert unpaywall.lookup("") is None


def test_returns_none_when_contact_email_not_configured(monkeypatch):
    monkeypatch.setattr(unpaywall.config, "SYSTEM_SENDER_EMAIL", "")
    assert unpaywall.lookup("10.1000/example") is None


def test_returns_pdf_url_from_best_oa_location(monkeypatch):
    monkeypatch.setattr(unpaywall.config, "SYSTEM_SENDER_EMAIL", "sender@example.com")
    monkeypatch.setattr(unpaywall.requests, "get", lambda *a, **k: _FakeResponse(
        200, {"best_oa_location": {"url_for_pdf": "https://example.com/paper.pdf"}}
    ))
    assert unpaywall.lookup("10.1000/example") == "https://example.com/paper.pdf"


def test_falls_back_to_plain_url_when_no_pdf_link(monkeypatch):
    monkeypatch.setattr(unpaywall.config, "SYSTEM_SENDER_EMAIL", "sender@example.com")
    monkeypatch.setattr(unpaywall.requests, "get", lambda *a, **k: _FakeResponse(
        200, {"best_oa_location": {"url": "https://example.com/landing-page"}}
    ))
    assert unpaywall.lookup("10.1000/example") == "https://example.com/landing-page"


def test_returns_none_when_no_oa_copy_exists(monkeypatch):
    monkeypatch.setattr(unpaywall.config, "SYSTEM_SENDER_EMAIL", "sender@example.com")
    monkeypatch.setattr(unpaywall.requests, "get", lambda *a, **k: _FakeResponse(
        200, {"best_oa_location": None}
    ))
    assert unpaywall.lookup("10.1000/example") is None


def test_returns_none_on_http_error(monkeypatch):
    monkeypatch.setattr(unpaywall.config, "SYSTEM_SENDER_EMAIL", "sender@example.com")
    monkeypatch.setattr(unpaywall.requests, "get", lambda *a, **k: _FakeResponse(404))
    assert unpaywall.lookup("10.1000/does-not-exist") is None


def test_returns_none_when_request_raises(monkeypatch):
    import requests as real_requests

    def _raise(*a, **k):
        raise real_requests.exceptions.Timeout("simulated timeout")

    monkeypatch.setattr(unpaywall.config, "SYSTEM_SENDER_EMAIL", "sender@example.com")
    monkeypatch.setattr(unpaywall.requests, "get", _raise)
    assert unpaywall.lookup("10.1000/example") is None
