from dataclasses import dataclass

import numpy as np

from app.session_store import Session

NOT_FOUND = "В загруженных документах этого нет."

SYSTEM_PROMPT = f"""Ты — ассистент, который отвечает на вопросы строго по фрагментам документов компании.
Правила:
1. Используй только информацию из фрагментов. Не добавляй знаний извне и не делай предположений.
2. После каждого утверждения ставь номер фрагмента-источника в квадратных скобках, например [1] или [2][3].
3. Если во фрагментах нет ответа на вопрос, ответь ровно фразой: «{NOT_FOUND}»
4. Отвечай по-русски, кратко и по делу."""


class NoDocuments(Exception):
    pass


@dataclass(frozen=True)
class Source:
    n: int
    file: str
    loc: str
    text: str


@dataclass(frozen=True)
class Answer:
    text: str
    sources: list[Source]


def _top_k(matrix: np.ndarray, query: np.ndarray, k: int) -> list[int]:
    m = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)
    q = query / np.linalg.norm(query)
    scores = m @ q
    return [int(i) for i in np.argsort(-scores, kind="stable")[: min(k, len(scores))]]


def _user_prompt(question: str, sources: list[Source]) -> str:
    fragments = "\n\n".join(f"[{s.n}] ({s.file}, {s.loc})\n{s.text}" for s in sources)
    return f"Фрагменты документов:\n\n{fragments}\n\nВопрос: {question}"


def answer(client, session: Session, question: str, top_k: int = 20, top_n: int = 5) -> Answer:
    if not session.chunks or session.vectors is None:
        raise NoDocuments
    q = client.embed([question])[0]
    candidates = _top_k(session.vectors, q, top_k)
    ranked = client.rerank(question, [session.chunks[i].text for i in candidates], top_n=min(top_n, len(candidates)))
    picked = [session.chunks[candidates[idx]] for idx, _ in ranked]
    sources = [Source(n, c.file, c.loc, c.text) for n, c in enumerate(picked, start=1)]

    text = client.chat(SYSTEM_PROMPT, _user_prompt(question, sources))
    # Только ответ целиком: фраза внутри частичного ответа не должна стирать найденное.
    if text.strip().rstrip(".").strip() == NOT_FOUND.rstrip("."):
        return Answer(NOT_FOUND, [])
    # Показываем только то, на что модель сослалась: несвязанные фрагменты создают ложное впечатление обоснованности.
    return Answer(text, [s for s in sources if f"[{s.n}]" in text])
