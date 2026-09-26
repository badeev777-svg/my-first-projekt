import numpy as np


class FakeClient:
    """Одинаковые векторы + реранкер, разворачивающий порядок — чтобы проверять маппинг индексов."""

    def __init__(self, chat_reply: str = "Ответ [1]", dim: int = 4):
        self.chat_reply = chat_reply
        self.dim = dim
        self.last_user_prompt: str | None = None

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.ones((len(texts), self.dim), dtype=np.float32)

    def rerank(self, query: str, documents: list[str], top_n: int) -> list[tuple[int, float]]:
        return [(i, 1.0 / (1 + n)) for n, i in enumerate(reversed(range(len(documents))))][:top_n]

    def chat(self, system: str, user: str) -> str:
        self.last_user_prompt = user
        return self.chat_reply
