"""Analyzes leads using Claude API with Effort Control."""
import json
import logging
from typing import Optional

from anthropic import Anthropic

from app.config import ANTHROPIC_API_KEY

log = logging.getLogger(__name__)

client = Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Ты эксперт в анализе фриланс-заявок для веб-разработчика.
Анализируй заявку и возвращай структурированный JSON.
Будь лаконичен и точен."""

ANALYSIS_PROMPT = """Проанализируй заявку на фриланс-работу и верни JSON с результатами:

Текст заявки:
---
Источник: {source}
Название: {title}
Описание: {text}
Указанный бюджет: {budget}
---

Верни ТОЛЬКО валидный JSON (без markdown и доп текста):
{{
  "relevance_score": <число 0-100, насколько релевантна для веб-разработчика>,
  "tags": <массив категорий: design, frontend, backend, fullstack, seo, marketing, mobile, devops, content, analytics>,
  "summary": <строка, 1-2 предложения, суть заявки>,
  "estimated_budget": <число, твоя оценка реального бюджета в рублях, или null>
}}

Правила:
- relevance_score 80+: веб-разработка, дизайн, SEO, контент, маркетинг
- relevance_score 40-79: имеет отношение но вторично
- relevance_score <40: не по профилю
- tags: выбери 1-3 наиболее подходящих
- summary: краткий анализ, что требуется
- estimated_budget: реалистичная оценка, если указан бюджет то приблизительно проверь его адекватность
"""


async def analyze_lead(
    source: str,
    title: Optional[str],
    text: str,
    budget: Optional[int]
) -> dict:
    """Analyze a lead using Claude Opus 4.8 with Effort Control.

    Returns analysis dict with relevance_score, tags, summary, estimated_budget.
    Uses low effort for faster processing and fewer tokens.
    """
    if not ANTHROPIC_API_KEY:
        log.warning("ANTHROPIC_API_KEY not set, skipping analysis")
        return {}

    prompt = ANALYSIS_PROMPT.format(
        source=source,
        title=title or "Без названия",
        text=text,
        budget=budget or "Не указан"
    )

    try:
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            output_config={
                "effort": "low",  # Низкое усилие для быстрого анализа, экономим токены
            },
            thinking={
                "type": "adaptive",  # Адаптивное мышление для лучшего анализа релевантности
                "display": "omitted",  # Не показываем thinking процесс пользователю
            },
        )

        content = response.content[0].text.strip()

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            log.error(f"Failed to parse Claude response: {content}")
            return {}

        analysis = {
            "relevance_score": result.get("relevance_score"),
            "tags": ",".join(result.get("tags", [])) if result.get("tags") else None,
            "summary": result.get("summary"),
            "estimated_budget": result.get("estimated_budget"),
        }
        log.debug(f"Analysis complete: score={analysis['relevance_score']}, tags={analysis['tags']}")
        log.info(
            f"Tokens used: input={response.usage.input_tokens}, output={response.usage.output_tokens}"
        )
        return analysis

    except Exception as e:
        log.error(f"Analysis error: {e}")
        return {}
