import time

import httpx
import numpy as np

from app.config import Settings

EMBED_BATCH = 32


class CloudRuError(Exception):
    pass


class CloudRuClient:
    def __init__(self, settings: Settings, http: httpx.Client | None = None, retry_delay: float = 1.0):
        self._s = settings
        self._http = http or httpx.Client(base_url=settings.cloudru_base_url, timeout=settings.http_timeout_seconds)
        self._headers = {"Authorization": f"Bearer {settings.cloudru_api_key}"}
        self._retry_delay = retry_delay

    def _post(self, path: str, payload: dict) -> dict:
        err: Exception | None = None
        for attempt in (1, 2):
            try:
                r = self._http.post(path, json=payload, headers=self._headers)
            except httpx.TransportError as e:
                err = e
            else:
                # 4xx — ключ/биллинг/запрос: повтор не поможет и может списать деньги дважды.
                if 400 <= r.status_code < 500:
                    raise CloudRuError(f"cloud.ru HTTP {r.status_code}")
                if r.status_code < 400:
                    return r.json()
                err = CloudRuError(f"cloud.ru HTTP {r.status_code}")
            if attempt == 1:
                time.sleep(self._retry_delay)
        raise CloudRuError("cloud.ru unavailable") from err

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), EMBED_BATCH):
            data = self._post("/embeddings", {"model": self._s.embed_model, "input": texts[i : i + EMBED_BATCH]})
            items = sorted(data["data"], key=lambda x: x.get("index", 0))
            vectors.extend(item["embedding"] for item in items)
        return np.asarray(vectors, dtype=np.float32)

    def rerank(self, query: str, documents: list[str], top_n: int) -> list[tuple[int, float]]:
        data = self._post(
            "/rerank",
            {"model": self._s.rerank_model, "query": query, "documents": documents, "top_n": top_n},
        )
        return [(r["index"], r["relevance_score"]) for r in data["results"]]

    def chat(self, system: str, user: str) -> str:
        data = self._post(
            "/chat/completions",
            {
                "model": self._s.chat_model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": 0.1,
            },
        )
        return data["choices"][0]["message"]["content"].strip()
