import asyncio

from app.agent import PAID_SPLIT, REPORT_MARKER, AgentStore, Session, ensure_paid_split
from app.routers.chat import _extract_score


def test_progress_zero_at_start():
    s = Session()
    assert s.progress() == 0


def test_progress_scales_with_msg_count():
    s = Session(msg_count=6)
    assert s.progress() == round(6 / 13 * 100)


def test_progress_capped_below_100_until_finished():
    s = Session(msg_count=20)
    assert s.progress() == 95


def test_progress_100_when_finished():
    s = Session(msg_count=3, finished=True)
    assert s.progress() == 100


SAMPLE_REPORT = """
## 📊 Маркетинговый анализ: Кофейня "Зерно"

### 0. Скоринг зрелости маркетинга

**Общий балл: 62/100**

| Категория | Балл | Макс |
|-----------|------|------|
| Позиционирование и УТП | 14 | 25 |
| Целевая аудитория и каналы | 18 | 25 |
| Конкурентная позиция | 12 | 25 |
| Готовность к масштабированию | 18 | 25 |

---

### 1. Профиль бизнеса
...
"""


def test_extract_score_parses_total_and_categories():
    score = _extract_score(SAMPLE_REPORT)
    assert score is not None
    assert score["total"] == 62
    assert score["categories"] == [
        {"name": "Позиционирование и УТП", "score": 14, "max": 25},
        {"name": "Целевая аудитория и каналы", "score": 18, "max": 25},
        {"name": "Конкурентная позиция", "score": 12, "max": 25},
        {"name": "Готовность к масштабированию", "score": 18, "max": 25},
    ]


def test_extract_score_returns_none_when_absent():
    assert _extract_score("### 1. Профиль бизнеса\nбез скоринга") is None


# The LLM output is not a fixed template — it may render the section-1 heading
# differently (extra spacing, no leading "1.", etc). The parser must not fall
# back to scanning to the end of the report, or it can pick up unrelated tables.
MALFORMED_BOUNDARY_REPORT = """
## 📊 Маркетинговый анализ: Кофейня "Зерно"

### 0. Скоринг зрелости маркетинга

**Общий балл: 62/100**

| Категория | Балл | Макс |
|-----------|------|------|
| Позиционирование и УТП | 14 | 25 |
| Целевая аудитория и каналы | 18 | 25 |
| Конкурентная позиция | 12 | 25 |
| Готовность к масштабированию | 18 | 25 |

---

## Профиль бизнеса (без "### 1.")

| Клиентов/мес | 12 | 40 | 60 |

### 9. Финансовая модель

| Показатель | Текущий | Через год |
|---|---|---|
| Клиентов/мес | 40 | 90 |
"""


def test_extract_score_ignores_unrelated_tables_when_boundary_heading_differs():
    score = _extract_score(MALFORMED_BOUNDARY_REPORT)
    assert score is not None
    assert score["total"] == 62
    assert score["categories"] == [
        {"name": "Позиционирование и УТП", "score": 14, "max": 25},
        {"name": "Целевая аудитория и каналы", "score": 18, "max": 25},
        {"name": "Конкурентная позиция", "score": 12, "max": 25},
        {"name": "Готовность к масштабированию", "score": 18, "max": 25},
    ]


def test_extract_score_rejects_out_of_range_values():
    report = """
### 0. Скоринг зрелости маркетинга

**Общий балл: 200/100**

| Категория | Балл | Макс |
|-----------|------|------|
| Позиционирование и УТП | 14 | 25 |
| Целевая аудитория и каналы | 18 | 25 |
| Конкурентная позиция | 12 | 25 |
| Готовность к масштабированию | 18 | 25 |
"""
    assert _extract_score(report) is None


def test_extract_score_rejects_when_category_count_is_not_four():
    report = """
### 0. Скоринг зрелости маркетинга

**Общий балл: 62/100**

| Категория | Балл | Макс |
|-----------|------|------|
| Позиционирование и УТП | 14 | 25 |
| Целевая аудитория и каналы | 18 | 25 |
"""
    assert _extract_score(report) is None


def test_extract_score_parses_fraction_format_with_reason_column():
    report = """
### 0. Скоринг зрелости маркетинга

| Категория | Балл | Обоснование |
|-----------|------|-------------|
| Позиционирование и УТП | **15/25** | Свои обжарка и скорость. |
| Целевая аудитория и каналы | **18/25** | Ядро определено. |
| Конкурентная позиция | 12/25 | Конкуренты известны. |
| Готовность к масштабированию | **10 / 25** | CRM нет. |

**Общий балл: 55/100**

### 1. Профиль бизнеса
| Стадия | 1 | 2 |
"""
    score = _extract_score(report)
    assert score == {
        "total": 55,
        "categories": [
            {"name": "Позиционирование и УТП", "score": 15, "max": 25},
            {"name": "Целевая аудитория и каналы", "score": 18, "max": 25},
            {"name": "Конкурентная позиция", "score": 12, "max": 25},
            {"name": "Готовность к масштабированию", "score": 10, "max": 25},
        ],
    }


def test_extract_score_parses_bold_numbers_in_template_format():
    report = """
### 0. Скоринг зрелости маркетинга

**Общий балл: 40/100**

| Категория | Балл | Макс |
|---|---|---|
| A | **10** | 25 |
| B | **10** | **25** |
| C | 10 | 25 |
| D | 10 | 25 |
"""
    score = _extract_score(report)
    assert score is not None
    assert [c["score"] for c in score["categories"]] == [10, 10, 10, 10]


def test_extract_score_total_as_table_row_falls_back_to_sum():
    report = """
### 0. Скоринг зрелости маркетинга

| Категория | Балл | Макс |
|-----------|------|------|
| Позиционирование и УТП | 12 | 25 |
| Целевая аудитория и каналы | 15 | 25 |
| Конкурентная позиция | 10 | 25 |
| Готовность к масштабированию | 8 | 25 |
| **Общий балл** | **45** | **100** |

---

### 1. Профиль бизнеса
"""
    score = _extract_score(report)
    assert score is not None
    assert score["total"] == 45
    assert len(score["categories"]) == 4


def test_extract_score_accepts_bold_label_total():
    report = SAMPLE_REPORT.replace("**Общий балл: 62/100**", "**Общий балл:** 62/100")
    score = _extract_score(report)
    assert score is not None and score["total"] == 62


def test_ensure_paid_split_inserts_before_section_7():
    report = "### 6. Каналы\nтекст\n\n### 7. Детальный план\nплатно\nМАРКЕТИНГОВЫЙ_АНАЛИЗ_ЗАВЕРШЁН"
    fixed = ensure_paid_split(report)
    free, paid = fixed.split(PAID_SPLIT)
    assert "### 6." in free and "### 7." not in free
    assert paid.lstrip().startswith("### 7. Детальный план")


def test_ensure_paid_split_keeps_existing_separator():
    report = f"### 6. A\n{PAID_SPLIT}\n### 7. B"
    assert ensure_paid_split(report) == report


def test_ensure_paid_split_ignores_inline_numbers():
    report = "### 1. Профиль\nшаг 7. не заголовок\n| 7. | x |"
    assert ensure_paid_split(report) == report


def test_chat_stores_report_with_paid_split(monkeypatch):
    import app.agent as agent

    async def fake_llm(history):
        return f"### 6. A\n\n### 7. B\n{REPORT_MARKER}"

    monkeypatch.setattr(agent, "_call_llm", fake_llm)
    s = AgentStore()
    sess = s.get_or_create("x")
    sess.msg_count = 10
    reply = asyncio.run(s.chat("x", "готово"))
    assert PAID_SPLIT in reply
    assert sess.report_text == reply
    assert sess.history[-1]["content"] == reply


def test_report_without_marker_is_still_finished(monkeypatch):
    import app.agent as agent

    async def fake_llm(messages):
        return "### 0. Скоринг зрелости маркетинга\n...\n### 7. Детальный план\nплатно"

    monkeypatch.setattr(agent, "_call_llm", fake_llm)
    s = AgentStore()
    sess = s.get_or_create("x")
    sess.msg_count = 10
    reply = asyncio.run(s.chat("x", "готово"))
    assert sess.finished
    assert REPORT_MARKER in reply and PAID_SPLIT in reply


def test_plain_question_is_not_a_report(monkeypatch):
    import app.agent as agent

    async def fake_llm(messages):
        return "**Какой у Вас средний чек?**"

    monkeypatch.setattr(agent, "_call_llm", fake_llm)
    s = AgentStore()
    sess = s.get_or_create("x")
    sess.msg_count = 10
    asyncio.run(s.chat("x", "ответ"))
    assert not sess.finished


def _run_llm_turn(monkeypatch, answers_before: int) -> tuple[list[dict], Session]:
    import app.agent as agent

    sent = []

    async def fake_llm(messages):
        sent.extend(messages)
        return "Следующий вопрос?"

    monkeypatch.setattr(agent, "_call_llm", fake_llm)
    s = AgentStore()
    sess = s.get_or_create("x")
    sess.msg_count = answers_before
    sess.history.append({"role": "assistant", "content": "Вопрос?"})
    asyncio.run(s.chat("x", "ответ"))
    return sent, sess


def test_interview_guard_added_before_min_answers(monkeypatch):
    import app.agent as agent

    sent, sess = _run_llm_turn(monkeypatch, agent.MIN_ANSWERS_BEFORE_REPORT - 2)
    assert sent[-1]["content"].startswith("ответ")
    assert "Отчёт пока НЕ формируй" in sent[-1]["content"]
    # the guard is request-only, never stored in the dialogue
    assert all("Служебно" not in m["content"] for m in sess.history)


def test_interview_guard_absent_after_min_answers(monkeypatch):
    import app.agent as agent

    sent, _ = _run_llm_turn(monkeypatch, agent.MIN_ANSWERS_BEFORE_REPORT - 1)
    assert sent[-1]["content"] == "ответ"


def test_undo_reverts_normal_two_message_turn():
    store = AgentStore()
    session = store.get_or_create("s1")
    session.history = [
        {"role": "assistant", "content": "Q1"},
        {"role": "user", "content": "A1"},
        {"role": "assistant", "content": "Q2"},
    ]
    session.turn_starts = [1]
    session.msg_count = 1

    result = store.undo("s1")

    assert result == "Q1"
    assert session.history == [{"role": "assistant", "content": "Q1"}]
    assert session.msg_count == 0
    assert session.turn_starts == []


def test_undo_reverts_three_message_site_fetch_turn():
    store = AgentStore()
    session = store.get_or_create("s1")
    session.history = [
        {"role": "assistant", "content": "Q1"},
        {"role": "user", "content": "A1 с сайтом"},
        {"role": "user", "content": "[ДАННЫЕ С САЙТА КЛИЕНТА] текст с сайта"},
        {"role": "assistant", "content": "Q2"},
    ]
    session.turn_starts = [1]
    session.msg_count = 1

    result = store.undo("s1")

    assert result == "Q1"
    assert session.history == [{"role": "assistant", "content": "Q1"}]
    assert session.msg_count == 0
    assert session.turn_starts == []


def test_undo_returns_none_when_finished():
    store = AgentStore()
    session = store.get_or_create("s1")
    session.history = [{"role": "assistant", "content": "Q1"}]
    session.turn_starts = [0]
    session.finished = True

    assert store.undo("s1") is None


def test_undo_returns_none_when_no_turns_recorded():
    store = AgentStore()
    store.get_or_create("s1")

    assert store.undo("s1") is None
