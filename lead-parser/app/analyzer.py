"""Analyzes leads using Polza.ai API (Claude via OpenAI-compatible endpoint)."""
import json
import logging
from typing import Optional

import httpx

from app.config import POLZA_API_KEY

log = logging.getLogger(__name__)

POLZA_URL = "https://polza.ai/api/v1/chat/completions"
MODEL = "anthropic/claude-haiku-4.5"

SYSTEM_PROMPT = """Ты эксперт в анализе фриланс-заявок для веб-разработчика.
Анализируй заявку и возвращай структурированный JSON.
Будь лаконичен и точен."""

TEXT_LIMIT = 1500


def _truncate(text: str, limit: int = TEXT_LIMIT) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_space = cut.rfind(" ")
    return cut[:last_space] if last_space > limit * 0.8 else cut


ANALYSIS_PROMPT = """Проанализируй заявку на фриланс-работу и верни JSON с результатами:

Текст заявки:
---
Источник: {source}
Название: {title}
Ссылка: {url}
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
    budget: Optional[int],
    url: Optional[str] = None,
) -> dict:
    if not POLZA_API_KEY:
        log.warning("POLZA_API_KEY not set, skipping analysis")
        return {}

    prompt = ANALYSIS_PROMPT.format(
        source=source,
        title=title or "Без названия",
        url=url or "Не указана",
        text=_truncate(text),
        budget=budget or "Не указан",
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                POLZA_URL,
                headers={
                    "Authorization": f"Bearer {POLZA_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "max_tokens": 400,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"].strip()

        # Strip possible markdown code fences
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)

        score = result.get("relevance_score")
        if not isinstance(score, (int, float)) or not (0 <= score <= 100):
            log.warning(f"Invalid relevance_score from LLM: {score!r}, defaulting to 0")
            score = 0

        analysis = {
            "relevance_score": score,
            "tags": ",".join(result.get("tags", [])) if result.get("tags") else None,
            "summary": result.get("summary"),
            "estimated_budget": result.get("estimated_budget"),
        }
        usage = data.get("usage", {})
        log.debug(
            f"Analysis complete: score={analysis['relevance_score']}, tags={analysis['tags']}"
        )
        log.info(
            f"Tokens used: input={usage.get('prompt_tokens')}, output={usage.get('completion_tokens')}"
        )
        return analysis

    except json.JSONDecodeError as e:
        log.error(f"Failed to parse LLM response: {e}")
        return {}
    except Exception as e:
        log.error(f"Analysis error: {type(e).__name__}: {e}")
        return {}
