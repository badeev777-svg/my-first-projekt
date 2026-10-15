import httpx
import pytest

from app.config import Settings
from app.llm_client import CloudRuLLM, FakeLLM, LLMError, LLMTimeout


def make(handler) -> tuple[CloudRuLLM, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    settings = Settings(cloudru_api_key="test-key", _env_file=None)
    http = httpx.Client(base_url="https://llm.test/v1", transport=httpx.MockTransport(wrapped))
    return CloudRuLLM(settings, http=http, retry_delay=0), seen


def ok(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_chat_returns_stripped_content_and_sends_model():
    llm, seen = make(lambda r: ok("  привет  "))
    assert llm.chat("sys", "user") == "привет"
    body = seen[0].read().decode()
    assert "GigaChat/GigaChat-2-Max" in body
    assert seen[0].headers["Authorization"] == "Bearer test-key"


def test_5xx_is_retried_once_then_succeeds():
    replies = iter([httpx.Response(502), ok("ок")])
    llm, seen = make(lambda r: next(replies))
    assert llm.chat("s", "u") == "ок"
    assert len(seen) == 2


def test_4xx_is_not_retried():
    llm, seen = make(lambda r: httpx.Response(402))
    with pytest.raises(LLMError):
        llm.chat("s", "u")
    assert len(seen) == 1


def test_timeout_twice_raises_llm_timeout():
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    llm, seen = make(boom)
    with pytest.raises(LLMTimeout):
        llm.chat("s", "u")
    assert len(seen) == 2


def test_malformed_body_raises_llm_error():
    llm, _ = make(lambda r: httpx.Response(200, json={"nope": 1}))
    with pytest.raises(LLMError):
        llm.chat("s", "u")


def test_demo_flag_when_key_empty():
    assert Settings(cloudru_api_key="  ", _env_file=None).demo is True
    assert Settings(cloudru_api_key="k", _env_file=None).demo is False


def test_fake_llm_records_calls():
    fake = FakeLLM(lambda s, u: f"{s}|{u}")
    assert fake.chat("a", "b") == "a|b"
    assert fake.calls == [("a", "b")]


@pytest.mark.parametrize("content", [None, 42, ["a"]])
def test_null_or_non_string_content_raises_llm_error(content):
    llm, _ = make(lambda r: httpx.Response(200, json={"choices": [{"message": {"content": content}}]}))
    with pytest.raises(LLMError):
        llm.chat("s", "u")
