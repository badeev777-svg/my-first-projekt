from openai import AsyncOpenAI
from src.config import Config

_client: AsyncOpenAI | None = None

MAX_HISTORY_MESSAGES = 8


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url="https://llm.api.cloud.yandex.net/foundationModels/v1",
            api_key="dummy",
            default_headers={
                "Authorization": f"Api-Key {Config.YANDEX_API_KEY}",
            },
        )
    return _client


def _model() -> str:
    return f"gpt://{Config.YANDEX_FOLDER_ID}/{Config.LLM_MODEL}"


async def get_claude_response(
    system_prompt: str,
    history: list[dict],
    user_message: str,
    max_tokens: int = 200,
    temperature: float = 0.7
) -> str:
    trimmed_history = history[-MAX_HISTORY_MESSAGES:] if len(history) > MAX_HISTORY_MESSAGES else history
    messages = [{"role": "system", "content": system_prompt}] + trimmed_history + [{"role": "user", "content": user_message}]

    response = await _get_client().chat.completions.create(
        model=_model(),
        max_tokens=max_tokens,
        temperature=temperature,
        messages=messages
    )

    return response.choices[0].message.content


async def get_initial_response(system_prompt: str, opener_message: str) -> str:
    response = await _get_client().chat.completions.create(
        model=_model(),
        max_tokens=200,
        temperature=0.7,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": opener_message},
        ]
    )

    return response.choices[0].message.content
