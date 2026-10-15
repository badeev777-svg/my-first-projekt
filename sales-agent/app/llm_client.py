import time
from typing import Callable, Protocol

import httpx

from app.config import Settings


class LLMError(Exception):
    pass


class LLMTimeout(LLMError):
    pass


class LLM(Protocol):
    def chat(self, system: str, user: str) -> str: ...


class CloudRuLLM:
    def __init__(self, settings: Settings, http: httpx.Client | None = None, retry_delay: float = 1.0):
        self._model = settings.chat_model
        self._http = http or httpx.Client(
            base_url=settings.cloudru_base_url, timeout=settings.llm_timeout_seconds
        )
        self._headers = {"Authorization": f"Bearer {settings.cloudru_api_key}"}
        self._retry_delay = retry_delay

    def chat(self, system: str, user: str) -> str:
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.1,
        }
        err: LLMError = LLMError("cloud.ru unavailable")
        for attempt in (1, 2):
            try:
                r = self._http.post("/chat/completions", json=payload, headers=self._headers)
            except httpx.TimeoutException:
                err = LLMTimeout("cloud.ru timeout")
            except httpx.TransportError:
                err = LLMError("cloud.ru unavailable")
            else:
                # 4xx — ключ/биллинг/запрос: повтор не поможет и может списать деньги дважды.
                if 400 <= r.status_code < 500:
                    raise LLMError(f"cloud.ru HTTP {r.status_code}")
                if r.status_code < 400:
                    try:
                        content = r.json()["choices"][0]["message"]["content"]
                    except (ValueError, KeyError, IndexError, TypeError) as e:
                        raise LLMError("cloud.ru bad response") from e
                    if not isinstance(content, str):
                        raise LLMError("cloud.ru bad response: content is not text")
                    return content.strip()
                err = LLMError(f"cloud.ru HTTP {r.status_code}")
            if attempt == 1:
                time.sleep(self._retry_delay)
        raise err


class FakeLLM:
    """Модель для тестов: responder(system, user) возвращает текст или бросает исключение."""

    def __init__(self, responder: Callable[[str, str], str]):
        self._responder = responder
        self.calls: list[tuple[str, str]] = []

    def chat(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self._responder(system, user)
