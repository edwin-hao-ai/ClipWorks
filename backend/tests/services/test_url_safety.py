"""URL 安全校验测试：SSRF 防护、重定向逐跳校验、大小与 Content-Type 限制。"""

import pytest

from app.services import url_safety
from app.services.url_safety import UnsafeURLError, safe_get, validate_public_http_url


def _public_addrinfo(ip="93.184.216.34"):
    # getaddrinfo 返回结构：(family, type, proto, canonname, sockaddr)
    return [(2, 1, 6, "", (ip, 0))]


# ---------- validate_public_http_url ----------


def test_rejects_non_http_scheme():
    for bad in ("ftp://example.com/a", "file:///etc/passwd", "javascript:alert(1)", ""):
        with pytest.raises(UnsafeURLError):
            validate_public_http_url(bad)


def test_rejects_missing_host():
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("http:///path-only")


@pytest.mark.parametrize(
    "host",
    [
        "http://localhost/",
        "http://127.0.0.1/",
        "http://127.0.0.1:8000/health",
        "http://0.0.0.0/",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://172.16.0.1/",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata
        "http://[::1]/",
    ],
)
def test_rejects_private_or_local_literal(host):
    with pytest.raises(UnsafeURLError):
        validate_public_http_url(host)


def test_rejects_host_resolving_to_private(monkeypatch):
    monkeypatch.setattr(
        url_safety.socket, "getaddrinfo", lambda *a, **k: _public_addrinfo("10.1.2.3")
    )
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("http://evil.example.com/")


def test_rejects_dns_failure(monkeypatch):
    import socket

    def boom(*a, **k):
        raise socket.gaierror("nxdomain")

    monkeypatch.setattr(url_safety.socket, "getaddrinfo", boom)
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("http://does-not-exist.example/")


def test_accepts_public_host(monkeypatch):
    monkeypatch.setattr(
        url_safety.socket, "getaddrinfo", lambda *a, **k: _public_addrinfo("93.184.216.34")
    )
    assert validate_public_http_url("http://example.com/path") == "http://example.com/path"


# ---------- safe_get ----------


class _FakeResponse:
    def __init__(self, *, status=200, headers=None, content=b"", is_redirect=False):
        self.status_code = status
        self.headers = headers or {}
        self.content = content
        self.is_redirect = is_redirect

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


class _FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.requested = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, url, headers=None):
        self.requested.append(url)
        if not self._responses:
            raise AssertionError("no fake response queued")
        return self._responses.pop(0)


def test_safe_get_returns_body_and_validates(monkeypatch):
    monkeypatch.setattr(url_safety.socket, "getaddrinfo", lambda *a, **k: _public_addrinfo())
    fake = _FakeClient([_FakeResponse(content=b"hello", headers={"content-type": "text/html"})])
    monkeypatch.setattr(url_safety.httpx, "Client", lambda **k: fake)

    body, resp = safe_get("http://example.com/", timeout=5, max_bytes=1024)
    assert body == b"hello"
    assert fake.requested == ["http://example.com/"]


def test_safe_get_follows_redirect_and_revalidates(monkeypatch):
    # 两跳都解析到公网；第二跳返回最终内容。
    monkeypatch.setattr(url_safety.socket, "getaddrinfo", lambda *a, **k: _public_addrinfo())
    fake = _FakeClient(
        [
            _FakeResponse(status=302, is_redirect=True, headers={"location": "http://example.net/final"}),
            _FakeResponse(content=b"ok"),
        ]
    )
    monkeypatch.setattr(url_safety.httpx, "Client", lambda **k: fake)

    body, _ = safe_get("http://example.com/start", timeout=5, max_bytes=1024)
    assert body == b"ok"
    assert fake.requested == ["http://example.com/start", "http://example.net/final"]


def test_safe_get_blocks_redirect_to_private(monkeypatch):
    # 第一跳公网，重定向到内网 IP -> 必须拒绝。
    def resolver(host, *a, **k):
        if host == "example.com":
            return _public_addrinfo("93.184.216.34")
        return _public_addrinfo("127.0.0.1")

    monkeypatch.setattr(url_safety.socket, "getaddrinfo", resolver)
    fake = _FakeClient(
        [_FakeResponse(status=301, is_redirect=True, headers={"location": "http://127.0.0.1/secret"})]
    )
    monkeypatch.setattr(url_safety.httpx, "Client", lambda **k: fake)

    with pytest.raises(UnsafeURLError):
        safe_get("http://example.com/", timeout=5, max_bytes=1024)


def test_safe_get_enforces_max_bytes_via_content_length(monkeypatch):
    monkeypatch.setattr(url_safety.socket, "getaddrinfo", lambda *a, **k: _public_addrinfo())
    fake = _FakeClient([_FakeResponse(content=b"small", headers={"content-length": "999999"})])
    monkeypatch.setattr(url_safety.httpx, "Client", lambda **k: fake)

    with pytest.raises(UnsafeURLError):
        safe_get("http://example.com/big", timeout=5, max_bytes=1024)


def test_safe_get_enforces_content_type(monkeypatch):
    monkeypatch.setattr(url_safety.socket, "getaddrinfo", lambda *a, **k: _public_addrinfo())
    fake = _FakeClient([_FakeResponse(content=b"<html>", headers={"content-type": "text/html"})])
    monkeypatch.setattr(url_safety.httpx, "Client", lambda **k: fake)

    with pytest.raises(UnsafeURLError):
        safe_get(
            "http://example.com/not-image",
            timeout=5,
            max_bytes=1024,
            allowed_content_types=("image/",),
        )


def test_safe_get_allows_empty_content_type(monkeypatch):
    monkeypatch.setattr(url_safety.socket, "getaddrinfo", lambda *a, **k: _public_addrinfo())
    fake = _FakeClient([_FakeResponse(content=b"imgbytes", headers={})])
    monkeypatch.setattr(url_safety.httpx, "Client", lambda **k: fake)

    body, _ = safe_get(
        "http://example.com/x",
        timeout=5,
        max_bytes=1024,
        allowed_content_types=("image/",),
    )
    assert body == b"imgbytes"


# ---------- 服务层集成：确认 SSRF 防护真正接到调用点（fail-soft） ----------


def test_scrape_url_returns_empty_on_private_ip():
    """字面内网 IP 在 helper 层即被拒，scrape_url 应 fail-soft 返回空结果，且不发起请求。"""
    from app.services.scraper import scrape_url

    result = scrape_url("http://127.0.0.1:8000/secret")
    assert result["title"] == ""
    assert result["images"] == []
    assert result["url"] == "http://127.0.0.1:8000/secret"


def test_download_image_returns_none_on_metadata_url(tmp_path, monkeypatch):
    """云元数据地址必须被拒；download_image fail-soft 返回 None，且不写出文件。"""
    from app.services import assets as assets_svc

    # 避免在测试里创建真实项目目录；把目录指到临时路径。
    monkeypatch.setattr(assets_svc, "_ensure_project_dir", lambda pid: str(tmp_path))
    assert assets_svc.download_image("http://169.254.169.254/latest/meta-data/", "proj") is None
    assert list(tmp_path.iterdir()) == []


# ---------- trusted_host_suffixes（fake-ip 代理环境兼容） ----------


def test_trusted_suffix_skips_dns_ip_check(monkeypatch):
    """白名单域名解析到保留段（如 fake-ip 198.18/15）也放行，且不调用 DNS。"""
    def boom(*a, **k):
        raise AssertionError("trusted host should not hit DNS")

    monkeypatch.setattr(url_safety.socket, "getaddrinfo", boom)
    url = "https://picsum.photos/seed/abc/1080/1920"
    assert validate_public_http_url(url, ("picsum.photos",)) == url


def test_trusted_suffix_matches_subdomain_and_boundary(monkeypatch):
    monkeypatch.setattr(url_safety.socket, "getaddrinfo", lambda *a, **k: _public_addrinfo())
    # 子域名命中
    assert validate_public_http_url("https://i.picsum.photos/id/1/200", ("picsum.photos",))
    # 非边界后缀（notpicsum.photos）不得命中，仍走 DNS 校验
    assert validate_public_http_url("https://notpicsum.photos/x", ("picsum.photos",))


def test_trusted_suffix_does_not_weaken_other_hosts(monkeypatch):
    monkeypatch.setattr(
        url_safety.socket, "getaddrinfo", lambda *a, **k: _public_addrinfo("198.18.3.177")
    )
    with pytest.raises(UnsafeURLError):
        validate_public_http_url("https://evil.example.com/x", ("picsum.photos",))


def test_safe_get_trusted_suffix_survives_redirect_to_reserved_ip(monkeypatch):
    """两跳都在白名单内：即使解析到 fake-ip 保留段也放行。"""
    monkeypatch.setattr(
        url_safety.socket, "getaddrinfo", lambda *a, **k: _public_addrinfo("198.18.3.177")
    )
    fake = _FakeClient(
        [
            _FakeResponse(status=302, is_redirect=True, headers={"location": "https://i.picsum.photos/id/10/1080/1920"}),
            _FakeResponse(content=b"img", headers={"content-type": "image/jpeg"}),
        ]
    )
    monkeypatch.setattr(url_safety.httpx, "Client", lambda **k: fake)

    body, _ = safe_get(
        "https://picsum.photos/seed/abc/1080/1920",
        timeout=5,
        max_bytes=1024,
        trusted_host_suffixes=("picsum.photos",),
    )
    assert body == b"img"


def test_safe_get_trusted_suffix_blocks_redirect_outside_allowlist(monkeypatch):
    """重定向跳出白名单到保留段主机时必须拒绝。"""
    monkeypatch.setattr(
        url_safety.socket, "getaddrinfo", lambda *a, **k: _public_addrinfo("198.18.3.177")
    )
    fake = _FakeClient(
        [_FakeResponse(status=302, is_redirect=True, headers={"location": "https://evil.example.com/x"})]
    )
    monkeypatch.setattr(url_safety.httpx, "Client", lambda **k: fake)

    with pytest.raises(UnsafeURLError):
        safe_get(
            "https://picsum.photos/seed/abc/1080/1920",
            timeout=5,
            max_bytes=1024,
            trusted_host_suffixes=("picsum.photos",),
        )
