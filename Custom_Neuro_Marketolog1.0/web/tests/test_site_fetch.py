import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

from app import site_fetch
from app.site_fetch import extract_url, _is_private_host, fetch_site_context, html_to_text


class _RedirectingServer:
    """Local HTTP server for exercising the redirect-walking logic in _fetch_html
    without hitting the real network (unavailable/unreliable in this sandbox)."""

    def __init__(self, routes: dict[str, tuple[int, dict, bytes]]) -> None:
        self._routes = routes
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                status, headers, body = outer._routes.get(
                    self.path, (404, {}, b"not found")
                )
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self._server.server_port
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._thread.join()

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"


def test_extract_url_finds_https_url():
    assert extract_url("Вот ссылка: https://zerno-coffee.ru/menu") == "https://zerno-coffee.ru/menu"


def test_extract_url_finds_bare_domain():
    assert extract_url("у нас сайт zerno-coffee.ru, заходите") == "zerno-coffee.ru"


def test_extract_url_none_for_no_site():
    assert extract_url("нет") is None
    assert extract_url("не знаю") is None
    assert extract_url("") is None
    assert extract_url("сайта пока нет, только инстаграм без ссылки") is None


def test_is_private_host_blocks_loopback_and_local():
    assert _is_private_host("127.0.0.1") is True
    assert _is_private_host("localhost") is True
    assert _is_private_host("10.0.0.5") is True
    assert _is_private_host("169.254.169.254") is True


def test_is_private_host_allows_public_ip():
    assert _is_private_host("8.8.8.8") is False


def test_html_to_text_strips_script_and_style():
    html = """
    <html><head><style>body{color:red}</style></head>
    <body>
        <script>alert('x')</script>
        <h1>Кофейня Зерно</h1>
        <p>Свежий кофе  и   выпечка</p>
    </body></html>
    """
    text = html_to_text(html)
    assert "color:red" not in text
    assert "alert" not in text
    assert "Кофейня Зерно" in text
    assert "Свежий кофе и выпечка" in text


_real_is_private_host = site_fetch._is_private_host


def _allow_loopback_block_others(host: str) -> bool:
    """Test-only stand-in for _is_private_host: 127.0.0.1 is allowed (so the local
    test server is reachable) but every other host is checked for real, so a redirect
    to an actually-private host (e.g. the metadata IP) is still blocked."""
    if host == "127.0.0.1":
        return False
    return _real_is_private_host(host)


def test_fetch_site_context_blocks_private_host_before_connecting():
    result = asyncio.run(fetch_site_context("http://127.0.0.1:1/"))
    assert result is None


def test_fetch_site_context_follows_same_host_redirect():
    with _RedirectingServer(
        {
            "/start": (302, {"Location": "/final"}, b""),
            "/final": (
                200,
                {"Content-Type": "text/html"},
                b"<html><body><h1>Zerno Coffee</h1></body></html>",
            ),
        }
    ) as server, patch(
        "app.site_fetch._is_private_host", side_effect=_allow_loopback_block_others
    ):
        result = asyncio.run(fetch_site_context(server.url("/start")))

    assert result is not None
    assert "Zerno Coffee" in result


def test_fetch_site_context_blocks_redirect_to_private_host():
    with _RedirectingServer(
        {
            "/start": (
                302,
                {"Location": "http://169.254.169.254/latest/meta-data/"},
                b"",
            ),
        }
    ) as server, patch(
        "app.site_fetch._is_private_host", side_effect=_allow_loopback_block_others
    ):
        result = asyncio.run(fetch_site_context(server.url("/start")))

    assert result is None
