import asyncio

from telegram import Bot

from app.config import get_settings
from app.skill_hunter.hunter import run


async def _main() -> None:
    settings = get_settings()
    bot = Bot(token=settings.telegram_bot_token)

    async def send_message(text: str) -> None:
        await bot.send_message(chat_id=settings.skill_hunter_chat_id, text=text)

    await run(settings.skill_hunter_niches, settings.skill_hunter_history_path, send_message)


if __name__ == "__main__":
    asyncio.run(_main())
