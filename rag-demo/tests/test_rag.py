import numpy as np
import pytest

from app.chunker import Chunk
from app.rag import NOT_FOUND, NoDocuments, Source, answer
from app.session_store import Session
from tests.fakes import FakeClient


def session_with(*chunks: Chunk) -> Session:
    return Session(id="s", created_at=0, files=[], chunks=list(chunks), vectors=np.ones((len(chunks), 4), dtype=np.float32))


A = Chunk("A.pdf", "стр. 1", "текст A")
B = Chunk("B.pdf", "стр. 2", "текст B")
C = Chunk("C.pdf", "стр. 3", "текст C")


def test_reranked_order_and_only_cited_sources_returned():
    client = FakeClient(chat_reply="Ответ по документу [1].")
    result = answer(client, session_with(A, B, C), "вопрос", top_n=2)
    # реранкер вернул C, затем B → C стал фрагментом [1]
    assert result.sources == [Source(1, "C.pdf", "стр. 3", "текст C")]
    assert result.text == "Ответ по документу [1]."


def test_prompt_contains_numbered_fragments_with_locations():
    client = FakeClient()
    answer(client, session_with(A, B, C), "Сколько дней отпуск?", top_n=2)
    prompt = client.last_user_prompt
    assert "[1] (C.pdf, стр. 3)\nтекст C" in prompt
    assert "[2] (B.pdf, стр. 2)\nтекст B" in prompt
    assert "Сколько дней отпуск?" in prompt
    assert "текст A" not in prompt


def test_not_found_answer_has_no_sources():
    client = FakeClient(chat_reply="В загруженных документах этого нет.")
    result = answer(client, session_with(A), "что-то")
    assert result.text == NOT_FOUND
    assert result.sources == []


def test_no_documents_raises():
    empty = Session(id="s", created_at=0)
    with pytest.raises(NoDocuments):
        answer(FakeClient(), empty, "вопрос")


def test_top_k_limits_candidates_sent_to_reranker():
    seen = {}
    client = FakeClient()
    original = client.rerank

    def spy(query, documents, top_n):
        seen["n"] = len(documents)
        return original(query, documents, top_n)

    client.rerank = spy
    answer(client, session_with(*[Chunk("f.pdf", f"стр. {i}", f"t{i}") for i in range(30)]), "q", top_k=20)
    assert seen["n"] == 20


def test_partial_not_found_keeps_cited_answer():
    reply = "Отпуск 28 дней [1]. В загруженных документах этого нет сведений о директоре."
    result = answer(FakeClient(chat_reply=reply), session_with(A), "отпуск и директор?")
    assert result.text == reply
    assert [s.n for s in result.sources] == [1]


def test_not_found_without_final_period_is_normalized():
    result = answer(FakeClient(chat_reply=" В загруженных документах этого нет "), session_with(A), "q")
    assert (result.text, result.sources) == (NOT_FOUND, [])
