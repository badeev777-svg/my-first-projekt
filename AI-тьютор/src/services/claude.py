from anthropic import AsyncAnthropic
from src.config import Config


async def get_claude_response(
    system_prompt: str,
    history: list[dict],
    user_message: str,
    max_tokens: int = 200,
    temperature: float = 0.7
) -> str:
    client = AsyncAnthropic(api_key=Config.ANTHROPIC_API_KEY)
    messages = history + [{"role": "user", "content": user_message}]

    response = await client.messages.create(
        model=Config.CLAUDE_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=messages
    )

    return response.content[0].text


async def get_initial_response(system_prompt: str, opener_message: str) -> str:
    client = AsyncAnthropic(api_key=Config.ANTHROPIC_API_KEY)

    response = await client.messages.create(
        model=Config.CLAUDE_MODEL,
        max_tokens=200,
        temperature=0.7,
        system=system_prompt,
        messages=[{"role": "user", "content": opener_message}]
    )

    return response.content[0].text
