from app.agent import Session
from app.routers.chat import _extract_score


def test_progress_zero_at_start():
    s = Session()
    assert s.progress() == 0


def test_progress_scales_with_msg_count():
    s = Session(msg_count=6)
    assert s.progress() == 50


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
