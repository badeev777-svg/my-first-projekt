import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit

import httpx

from app.config import settings

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_BARE_DOMAIN_RE = re.compile(
    r"\b(?:[a-zA-Zа-яА-ЯёЁ0-9](?:[a-zA-Zа-яА-ЯёЁ0-9-]{0,61}[a-zA-Zа-яА-ЯёЁ0-9])?\.)+"
    r"[a-zA-Zа-яА-ЯёЁ]{2,}\b"
)
_SKIP_TAGS = {"script", "style", "noscript"}


def extract_url(text: str) -> str | None:
    match = _URL_RE.search(text)
    if match:
        return match.group(0).rstrip(".,;!?)\"'")
    match = _BARE_DOMAIN_RE.search(text)
    if match:
        return match.group(0).rstrip(".,;!?)\"'")
    return None


def _is_private_host(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        pass

    if host.lower() == "localhost":
        return True

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True

    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return True
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return True
    return False


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            data = data.strip()
            if data:
                self.chunks.append(data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return re.sub(r"\s+", " ", " ".join(parser.chunks)).strip()


def _normalize_url(url: str) -> str | None:
    if "://" not in url:
        url = f"https://{url}"
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    return urlunsplit(parts)


async def fetch_site_context(url: str) -> str | None:
    normalized = _normalize_url(url)
    if not normalized:
        return None

    host = urlsplit(normalized).hostname
    if not host or _is_private_host(host):
        return None

    try:
        async with httpx.AsyncClient(
            timeout=settings.SITE_FETCH_TIMEOUT,
            follow_redirects=True,
            max_redirects=3,
        ) as client:
            async with client.stream("GET", normalized) as resp:
                if resp.status_code != 200:
                    return None
                content_type = resp.headers.get("content-type", "")
                if "text/html" not in content_type.lower():
                    return None

                redirect_host = urlsplit(str(resp.url)).hostname
                if not redirect_host or _is_private_host(redirect_host):
                    return None

                body = b""
                async for chunk in resp.aiter_bytes():
                    body += chunk
                    if len(body) > settings.SITE_FETCH_MAX_BYTES:
                        break
                html = body[: settings.SITE_FETCH_MAX_BYTES].decode("utf-8", errors="ignore")
    except (httpx.HTTPError, OSError):
        return None

    text = html_to_text(html)
    if not text:
        return None
    return text[: settings.SITE_FETCH_MAX_CHARS]
