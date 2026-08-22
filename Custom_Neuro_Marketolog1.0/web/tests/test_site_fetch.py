from app.site_fetch import extract_url, _is_private_host, html_to_text


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
