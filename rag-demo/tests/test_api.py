import pytest
from fastapi.testclient import TestClient

from app.cloudru import CloudRuError
from app.config import Settings
from app.main import create_app
from app.session_store import SessionStore
from tests.fakes import FakeClient
from tests.helpers import make_docx

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def make_settings(**kw):
    base = dict(cloudru_api_key="k", access_code="secret", cookie_secure=False, max_files=2, max_questions=2)
    base.update(kw)
    return Settings(_env_file=None, **base)


@pytest.fixture
def fake():
    return FakeClient(chat_reply="Отпуск 28 дней [1].")


@pytest.fixture
def api(fake):
    with TestClient(create_app(make_settings(), client=fake, store=SessionStore(3600))) as c:
        yield c


def login(c):
    assert c.post("/api/login", json={"code": "secret"}).status_code == 200


def upload(c, name="Регламент.docx", paragraphs=("Отпуск 28 дней",)):
    return c.post("/api/upload", files=[("files", (name, make_docx(list(paragraphs)), DOCX_MIME))])


def test_index_served(api):
    assert api.get("/").status_code == 200


def test_wrong_code(api):
    r = api.post("/api/login", json={"code": "nope"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Неверный код доступа."


def test_no_session_is_401_with_message(api):
    r = api.post("/api/ask", json={"question": "x"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Сессия завершена, документы удалены. Загрузите их снова."


def test_ask_before_upload(api):
    login(api)
    r = api.post("/api/ask", json={"question": "x"})
    assert r.status_code == 400
    assert r.json()["detail"] == "Сначала загрузите документы."


def test_upload_and_ask_returns_cited_sources(api):
    login(api)
    r = upload(api)
    assert r.status_code == 200
    assert r.json()["files"] == ["Регламент.docx"]
    r = api.post("/api/ask", json={"question": "Сколько дней отпуск?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "Отпуск 28 дней [1]."
    assert body["sources"] == [{"n": 1, "file": "Регламент.docx", "loc": "абз. 1", "text": "Отпуск 28 дней"}]
    assert api.get("/api/session").json() == {"files": ["Регламент.docx"], "questions_left": 1}


def test_duplicate_upload_rejected(api):
    login(api)
    upload(api)
    r = upload(api)
    assert r.status_code == 400
    assert r.json()["detail"] == "Файл «Регламент.docx» уже загружен."


def test_unsupported_format(api):
    login(api)
    r = api.post("/api/upload", files=[("files", ("a.txt", b"hi", "text/plain"))])
    assert r.status_code == 400
    assert r.json()["detail"] == "Поддерживаются PDF и DOCX."


def test_file_count_limit(api):
    login(api)
    upload(api, "1.docx")
    upload(api, "2.docx")
    r = upload(api, "3.docx")
    assert r.status_code == 400
    assert r.json()["detail"] == "Можно загрузить не больше 2 файлов."


def test_file_size_limit(fake):
    with TestClient(create_app(make_settings(max_file_mb=0), client=fake, store=SessionStore(3600))) as c:
        login(c)
        r = upload(c)
        assert r.status_code == 400
        assert r.json()["detail"] == "Файл «Регламент.docx» больше 0 МБ."


def test_question_limit(api):
    login(api)
    upload(api)
    for _ in range(2):
        assert api.post("/api/ask", json={"question": "q"}).status_code == 200
    r = api.post("/api/ask", json={"question": "q"})
    assert r.status_code == 400
    assert r.json()["detail"] == "Лимит 2 вопросов на сессию исчерпан."


def test_cloud_error_is_503(fake):
    def boom(texts):
        raise CloudRuError("down")

    fake.embed = boom
    with TestClient(create_app(make_settings(), client=fake, store=SessionStore(3600))) as c:
        login(c)
        r = upload(c)
        assert r.status_code == 503
        assert r.json()["detail"] == "Сервис ИИ временно недоступен, попробуйте через минуту."


def test_delete_session(api):
    login(api)
    upload(api)
    assert api.delete("/api/session").status_code == 200
    assert api.post("/api/ask", json={"question": "q"}).status_code == 401


def test_expired_session(fake):
    now = [0.0]
    store = SessionStore(60, clock=lambda: now[0])
    with TestClient(create_app(make_settings(), client=fake, store=store)) as c:
        login(c)
        now[0] = 61
        r = c.get("/api/session")
        assert r.status_code == 401
        assert r.json()["detail"] == "Сессия завершена, документы удалены. Загрузите их снова."
