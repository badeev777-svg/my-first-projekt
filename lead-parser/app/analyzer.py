"""Analyzes leads using OpenRouter/Claude."""
import json
import logging
import os
from typing import Optional

import httpx

log = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

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
    """Analyze a lead using Claude via OpenRouter. Returns analysis dict."""
    if not OPENROUTER_API_KEY:
        log.warning("OPENROUTER_API_KEY not set, skipping analysis")
        return {}

    prompt = ANALYSIS_PROMPT.format(
        source=source,
        title=title or "Без названия",
        text=text,
        budget=budget or "Не указан"
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": "https://lead-parser.local",
                    "X-Title": "Lead Parser",
                },
                json={
                    "model": "anthropic/claude-3-haiku",
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                }
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"].strip()

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
            return analysis

    except httpx.HTTPError as e:
        log.error(f"OpenRouter API error: {e}")
        return {}
    except Exception as e:
        log.error(f"Analysis error: {e}")
        return {}
