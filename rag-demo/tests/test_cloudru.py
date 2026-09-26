import json

import httpx
import pytest

from app.cloudru import EMBED_BATCH, CloudRuClient, CloudRuError
from app.config import Settings

BASE = "https://foundation-models.api.cloud.ru/v1"


def make_client(handler):
    settings = Settings(cloudru_api_key="k", access_code="code-1234", _env_file=None)
    http = httpx.Client(base_url=BASE, transport=httpx.MockTransport(handler))
    return CloudRuClient(settings, http=http, retry_delay=0)


def test_embed_batches_and_keeps_order():
    calls = []

    def handler(request):
        body = json.loads(request.content)
        assert request.url.path == "/v1/embeddings"
        assert request.headers["Authorization"] == "Bearer k"
        assert body["model"] == "BAAI/bge-m3"
        calls.append(len(body["input"]))
        data = [{"index": i, "embedding": [float(t.split("-")[1]), 0.0]} for i, t in enumerate(body["input"])]
        return httpx.Response(200, json={"data": data[::-1]})  # API может вернуть в другом порядке

    texts = [f"t-{i}" for i in range(EMBED_BATCH + 5)]
    vecs = make_client(handler).embed(texts)
    assert calls == [EMBED_BATCH, 5]
    assert vecs.shape == (EMBED_BATCH + 5, 2)
    assert vecs[:, 0].tolist() == [float(i) for i in range(EMBED_BATCH + 5)]


def test_rerank_parses_results():
    def handler(request):
        body = json.loads(request.content)
        assert request.url.path == "/v1/rerank"
        assert body == {"model": "BAAI/bge-reranker-v2-m3", "query": "q", "documents": ["a", "b"], "top_n": 1}
        return httpx.Response(200, json={"results": [{"index": 1, "document": {"text": "b"}, "relevance_score": 0.9}]})

    assert make_client(handler).rerank("q", ["a", "b"], top_n=1) == [(1, 0.9)]


def test_chat_returns_content():
    def handler(request):
        body = json.loads(request.content)
        assert request.url.path == "/v1/chat/completions"
        assert body["messages"][0] == {"role": "system", "content": "sys"}
        return httpx.Response(200, json={"choices": [{"message": {"content": " ответ "}}]})

    assert make_client(handler).chat("sys", "user") == "ответ"


def test_retries_once_on_5xx_then_succeeds():
    responses = iter([httpx.Response(502), httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})])
    assert make_client(lambda r: next(responses)).chat("s", "u") == "ok"


def test_raises_after_second_failure():
    calls = []

    def handler(request):
        calls.append(1)
        raise httpx.ConnectError("down")

    with pytest.raises(CloudRuError):
        make_client(handler).chat("s", "u")
    assert len(calls) == 2


def test_4xx_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(402)

    with pytest.raises(CloudRuError):
        make_client(handler).chat("s", "u")
    assert len(calls) == 1
