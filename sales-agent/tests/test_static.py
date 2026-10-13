from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"
SINKS = ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write")


@pytest.mark.parametrize("name", ["index.html", "admin.html"])
def test_no_html_injection_sinks(name):
    text = (STATIC / name).read_text(encoding="utf-8")
    assert [s for s in SINKS if s in text] == []
    assert "<script src=" not in text


def test_index_has_controls(make_client):
    r = make_client().http.get("/")
    assert r.status_code == 200
    for needle in ("Сбросить диалог", "Остановить автоответы", "Повторить", 'maxlength="2000"', "DEMO",
                   "randomUUID", "AI-помощник"):
        assert needle in r.text, needle


def test_admin_page_is_local_only(make_client):
    assert make_client().http.get("/admin").status_code == 403
    r = make_client(admin=True).http.get("/admin")
    assert r.status_code == 200 and "Заявки" in r.text
