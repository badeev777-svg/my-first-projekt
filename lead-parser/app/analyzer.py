"""Analyzes leads using OpenRouter API (Claude via OpenAI-compatible endpoint)."""
import json
import logging
from typing import Optional

import httpx

from app.config import OPENROUTER_API_KEY

log = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "anthropic/claude-3.5-haiku"

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
    if not OPENROUTER_API_KEY:
        log.warning("OPENROUTER_API_KEY not set, skipping analysis")
        return {}

    prompt = ANALYSIS_PROMPT.format(
        source=source,
        title=title or "Без названия",
        text=text[:1500],
        budget=budget or "Не указан",
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
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

        analysis = {
            "relevance_score": result.get("relevance_score"),
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
