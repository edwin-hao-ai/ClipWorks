"""URL safety helpers for outbound HTTP requests.

用户提供的 URL（素材链接、网页抓取）会被服务端主动发起请求，必须做 SSRF 防护：
拒绝解析到内网/回环/链路本地/保留地址的主机，限制协议为 http/https，
并对重定向逐跳重新校验，避免跳转绕过。同时限制响应大小，防止恶意大文件。
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

# 明确拒绝的本地主机名（无需 DNS 即可判定）。
_LOCAL_HOSTNAMES = {"localhost", "localhost.", "ip6-localhost", "ip6-loopback"}
_LOCAL_HOST_SUFFIXES = (".localhost", ".localhost.", ".local", ".local.", ".internal")


class UnsafeURLError(ValueError):
    """Raised when a URL is not safe to fetch from the server."""


def _is_disallowed_ip(ip: ipaddress._BaseAddress) -> bool:
    """内网/回环/链路本地/保留/多播/未指定地址一律视为不安全。"""
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _host_is_local(host: str) -> bool:
    h = host.strip().lower().rstrip(".")
    if h in _LOCAL_HOSTNAMES:
        return True
    return any(h.endswith(suffix.rstrip(".")) for suffix in _LOCAL_HOST_SUFFIXES)


def validate_public_http_url(url: str, trusted_host_suffixes: Iterable[str] = ()) -> str:
    """校验 URL 可安全由服务端访问。失败抛出 UnsafeURLError，成功返回原 URL。

    规则：仅允许 http/https；必须含主机名；拒绝本地主机名；
    解析主机到 IP 后，任一解析结果落入内网/保留段即拒绝（fail-closed：DNS 失败也拒绝）。

    trusted_host_suffixes：我方构造/可信 API 返回的固定域名白名单（如 picsum.photos）。
    命中白名单的主机跳过 DNS-IP 校验——在 fake-ip 代理环境（DNS 返回 198.18/15 保留段）
    下仍能正常访问，同时重定向逐跳仍受同一白名单约束，用户输入 URL 不受影响。
    """
    if not isinstance(url, str) or not url.strip():
        raise UnsafeURLError("empty url")

    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURLError(f"unsupported scheme: {parsed.scheme!r}")

    host = parsed.hostname
    if not host:
        raise UnsafeURLError("missing hostname")

    if _host_is_local(host):
        raise UnsafeURLError(f"local hostname not allowed: {host!r}")

    h = host.strip().lower().rstrip(".")
    for suffix in trusted_host_suffixes:
        s = suffix.strip().lower().rstrip(".")
        if s and (h == s or h.endswith("." + s)):
            return url

    # 直接是 IP 字面量时也要走同一段判定。
    try:
        literal = ipaddress.ip_address(host)
        if _is_disallowed_ip(literal):
            raise UnsafeURLError(f"disallowed ip: {host}")
        return url
    except ValueError:
        pass  # 不是 IP 字面量，继续 DNS 解析。

    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"dns resolution failed for {host!r}: {exc}") from exc

    if not infos:
        raise UnsafeURLError(f"dns resolution returned no addresses for {host!r}")

    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise UnsafeURLError(f"unparseable resolved address {ip_str!r}")
        if _is_disallowed_ip(ip):
            raise UnsafeURLError(f"{host!r} resolves to disallowed ip {ip_str}")

    return url


def _content_type_allowed(content_type: Optional[str], allowed: Iterable[str]) -> bool:
    """空 Content-Type 视为放行（部分图床不回），否则按前缀白名单匹配。"""
    if not content_type:
        return True
    ct = content_type.split(";", 1)[0].strip().lower()
    if not ct:
        return True
    return any(ct.startswith(prefix) for prefix in allowed)


def safe_get(
    url: str,
    *,
    timeout: float,
    headers: Optional[dict] = None,
    max_redirects: int = 5,
    max_bytes: int = 10 * 1024 * 1024,
    allowed_content_types: Optional[Iterable[str]] = None,
    trusted_host_suffixes: Iterable[str] = (),
) -> tuple[bytes, httpx.Response]:
    """对公网 URL 发起带 SSRF/大小/类型校验的 GET，返回 (body, response)。

    重定向逐跳重新走 validate_public_http_url，避免 302 跳到内网绕过。
    trusted_host_suffixes 见 validate_public_http_url——白名单主机跳过 DNS-IP 校验。
    """
    allowed = tuple(p.lower() for p in (allowed_content_types or ()))
    headers = headers or {}
    current = url

    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        for _ in range(max_redirects + 1):
            validate_public_http_url(current, trusted_host_suffixes)
            response = client.get(current, headers=headers)

            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise UnsafeURLError("redirect without Location header")
                current = urljoin(current, location)
                continue

            response.raise_for_status()

            if allowed and not _content_type_allowed(
                response.headers.get("content-type"), allowed
            ):
                raise UnsafeURLError(
                    f"unexpected content-type: {response.headers.get('content-type')!r}"
                )

            content_length = response.headers.get("content-length")
            if content_length:
                try:
                    declared_size = int(content_length)
                except ValueError:
                    declared_size = None  # 非法 Content-Length 忽略，下面按实际 body 兜底。
                if declared_size is not None and declared_size > max_bytes:
                    raise UnsafeURLError("response exceeds max_bytes")

            body = response.content
            if len(body) > max_bytes:
                raise UnsafeURLError("response exceeds max_bytes")
            return body, response

    raise UnsafeURLError("too many redirects")
