from openai import AsyncOpenAI
from src.config import Config


async def get_claude_response(
    system_prompt: str,
    history: list[dict],
    user_message: str,
    max_tokens: int = 200,
    temperature: float = 0.7
) -> str:
    client = AsyncOpenAI(
        api_key=Config.OPENROUTER_API_KEY,
        base_url="https://openrouter.io/api/v1"
    )
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_message}]

    response = await client.chat.completions.create(
        model=Config.LLM_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=messages
    )

    return response.choices[0].message.content


async def get_initial_response(system_prompt: str, opener_message: str) -> str:
    client = AsyncOpenAI(
        api_key=Config.OPENROUTER_API_KEY,
        base_url="https://openrouter.io/api/v1"
    )

    response = await client.chat.completions.create(
        model=Config.LLM_MODEL,
        max_tokens=200,
        temperature=0.7,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": opener_message}
        ]
    )

    return response.choices[0].message.content
