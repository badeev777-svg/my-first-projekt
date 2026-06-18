from pathlib import Path
from dataclasses import dataclass, field

import httpx

from app.config import settings

_BASE = Path(__file__).parent.parent.parent / "GPT_SYSTEM"
_INSTRUCTIONS = _BASE / "GPT_1_NeuroMarketing" / "Instructions.txt"
_KNOWLEDGE_DIR = _BASE / "knowledge"

HANDOFF_MARKER = "ВХОДНЫЕ ДАННЫЕ ДЛЯ AI-АРХИТЕКТОРА"


def _build_system_prompt() -> str:
    instructions = _INSTRUCTIONS.read_text(encoding="utf-8")
    blocks = []
    if _KNOWLEDGE_DIR.exists():
        for f in sorted(_KNOWLEDGE_DIR.rglob("*.md")):
            blocks.append(f"### {f.name}\n{f.read_text(encoding='utf-8')}")
    if not blocks:
        return instructions
    knowledge = "\n\n---\n\n".join(blocks)
    return (
        f"{instructions}\n\n---\n\n"
        "БАЗА ЗНАНИЙ (используй как справочник во время интервью):\n\n"
        f"{knowledge}"
    )


SYSTEM_PROMPT = _build_system_prompt()


_SCRIPTED_QUESTIONS = [
    "Чем занимается ваш бизнес и что вы продаёте?",
    "Кто ваш целевой клиент? Какую конкретную проблему вы для него решаете?",
    "Как сейчас приходят клиенты? Какие каналы привлечения используете и что работает лучше всего?",
    "Чем вы отличаетесь от конкурентов? В чём ваше главное преимущество для клиента?",
]


@dataclass
class Session:
    history: list[dict] = field(default_factory=list)
    handoff_block: str | None = None
    finished: bool = False
    msg_count: int = 0


class AgentStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get_or_create(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session()
        return self._sessions[session_id]

    def reset(self, session_id: str) -> None:
        self._sessions[session_id] = Session()

    async def start(self, session_id: str) -> str:
        self.reset(session_id)
        greeting = (
            "Здравствуйте! Я — Нейро-Маркетолог, AI-консультант по развитию бизнеса.\n\n"
            "Проведу диагностику за 10–15 минут: найду точки роста, слабые места в привлечении "
            "клиентов и возможности для автоматизации. Никаких советов без данных — только факты.\n\n"
            f"**{_SCRIPTED_QUESTIONS[0]}**"
        )
        session = self.get_or_create(session_id)
        session.history.append({"role": "assistant", "content": greeting})
        return greeting

    async def chat(self, session_id: str, user_text: str) -> str:
        session = self.get_or_create(session_id)
        session.msg_count += 1
        session.history.append({"role": "user", "content": user_text})

        # First 3 user answers → use scripted follow-up questions (indices 1-3)
        scripted_idx = session.msg_count  # 1st user msg → question index 1, etc.
        if scripted_idx < len(_SCRIPTED_QUESTIONS):
            reply = f"**{_SCRIPTED_QUESTIONS[scripted_idx]}**"
            session.history.append({"role": "assistant", "content": reply})
            return reply

        reply = await _call_llm(session.history)

        session.history.append({"role": "assistant", "content": reply})

        if HANDOFF_MARKER in reply:
            session.handoff_block = reply
            session.finished = True

        return reply

    def undo(self, session_id: str) -> str | None:
        session = self.get_or_create(session_id)
        # Keep the initial system greeting (first 2 entries); need ≥4 to undo
        if session.finished or len(session.history) < 4:
            return None
        session.history.pop()  # last AI response
        session.history.pop()  # last user message
        session.msg_count = max(0, session.msg_count - 1)
        return next(
            (m["content"] for m in reversed(session.history) if m["role"] == "assistant"),
            None,
        )

    def get_handoff(self, session_id: str) -> str | None:
        s = self._sessions.get(session_id)
        return s.handoff_block if s else None


store = AgentStore()


async def _call_llm(messages: list[dict]) -> str:
    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *messages,
                ],
                "max_tokens": settings.MAX_TOKENS,
                "temperature": 0.7,
            },
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
