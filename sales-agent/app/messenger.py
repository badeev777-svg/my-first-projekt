from dataclasses import dataclass

GREETING = "Здравствуйте! Я ИИ-менеджер Бизнес Генератора. Расскажите, какую задачу хотите решить — подскажу подходящий вариант и цену."
RESTART_WORDS = {"/start", "/new", "начать", "начать заново"}
LLM_DOWN_REPLY = "Модель сейчас не ответила. Отправьте сообщение ещё раз через минуту — оно не потеряется."
BUSY_REPLY = "Слишком много сообщений подряд. Подождите минуту и напишите снова."
CHANNELS = {"max:": "MAX", "vk:": "ВКонтакте", "avito:": "Avito"}
# Здесь Александр отвечает клиенту в том же чате: бот не шлёт ссылки на Telegram и молчит, пока диалог у человека.
IN_CHAT = ("vk:", "avito:")


@dataclass(frozen=True)
class Incoming:
    peer: str  # куда отвечать: user_id в MAX и VK, chat_id в Avito
    mid: str
    text: str | None  # None — пользователь нажал «Начать»
    from_owner: bool = False  # написал владелец (вручную или эхо ответа бота)


def channel_label(session_id: str) -> str:
    return next((name for prefix, name in CHANNELS.items() if session_id.startswith(prefix)), "сайт")


def in_chat(session_id: str) -> bool:
    return session_id.startswith(IN_CHAT)


def adapt_in_chat(reply: str) -> tuple[str, list[tuple[str, str]]]:
    return reply.replace("начните новый диалог", "напишите «Начать заново»"), []


def split_text(text: str, limit: int) -> list[str]:
    parts: list[str] = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = text.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    return parts + [text] if text else parts
