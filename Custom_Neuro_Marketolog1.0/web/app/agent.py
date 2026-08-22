from pathlib import Path
from dataclasses import dataclass, field

import httpx

from app.config import settings
from app.site_fetch import extract_url, fetch_site_context

_BASE = Path(__file__).parent.parent.parent / "GPT_SYSTEM"
_INSTRUCTIONS = _BASE / "GPT_1_NeuroMarketing" / "Instructions.txt"
_KNOWLEDGE_DIR = _BASE / "knowledge"

REPORT_MARKER = "МАРКЕТИНГОВЫЙ_АНАЛИЗ_ЗАВЕРШЁН"
PAID_SPLIT = "[PAID_START]"

TOTAL_QUESTIONS = 13

SITE_CONTEXT_LABEL = "[ДАННЫЕ С САЙТА КЛИЕНТА]"


class LLMUnavailableError(Exception):
    """Raised when the upstream LLM provider can't be reached (e.g. geo-block, outage)."""


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
    "Чем занимается ваш бизнес и что именно вы продаёте?",
    "Кто ваш типичный клиент? Какую проблему он приходит решать?",
    "Как сейчас приходят клиенты? Какие каналы используете — что работает лучше всего?",
    "Чем вы отличаетесь от конкурентов? В чём главное преимущество для клиента?",
    "Есть сайт или страница в соцсетях? Пришлите ссылку — учту это в анализе (если нет, просто напишите «нет»).",
]


@dataclass
class Session:
    history: list[dict] = field(default_factory=list)
    report_text: str | None = None
    finished: bool = False
    msg_count: int = 0
    turn_starts: list[int] = field(default_factory=list)

    def progress(self) -> int:
        if self.finished:
            return 100
        return min(95, round(self.msg_count / TOTAL_QUESTIONS * 100))


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
            f"Здравствуйте! Я — {settings.AGENT_NAME}, AI-консультант по маркетингу и росту бизнеса.\n\n"
            "Проведу диагностику за 10–15 минут: проанализирую Вашу аудиторию, конкурентов, "
            "найду точки роста и подготовлю персональный маркетинговый анализ.\n\n"
            f"**{_SCRIPTED_QUESTIONS[0]}**"
        )
        session = self.get_or_create(session_id)
        session.history.append({"role": "assistant", "content": greeting})
        return greeting

    async def chat(self, session_id: str, user_text: str) -> str:
        session = self.get_or_create(session_id)
        session.msg_count += 1
        history_len_before = len(session.history)
        session.history.append({"role": "user", "content": user_text})

        if settings.ENABLE_SITE_FETCH and session.msg_count == len(_SCRIPTED_QUESTIONS):
            url = extract_url(user_text)
            if url:
                site_text = await fetch_site_context(url)
                if site_text:
                    session.history.append({
                        "role": "user",
                        "content": (
                            f"{SITE_CONTEXT_LABEL} используй как факты для отчёта, "
                            f"это не реплика пользователя:\n\n{site_text}"
                        ),
                    })

        scripted_idx = session.msg_count
        if scripted_idx < len(_SCRIPTED_QUESTIONS):
            reply = f"**{_SCRIPTED_QUESTIONS[scripted_idx]}**"
            session.history.append({"role": "assistant", "content": reply})
            session.turn_starts.append(history_len_before)
            return reply

        try:
            reply = await _call_llm(session.history)
        except LLMUnavailableError:
            session.msg_count -= 1
            del session.history[history_len_before:]
            return (
                "Сервис временно недоступен — уже разбираемся. "
                f"Чтобы не терять время, напишите напрямую: {settings.CONTACT_LINK}"
            )

        session.history.append({"role": "assistant", "content": reply})
        session.turn_starts.append(history_len_before)

        if REPORT_MARKER in reply:
            session.report_text = reply
            session.finished = True

        return reply

    def undo(self, session_id: str) -> str | None:
        session = self.get_or_create(session_id)
        if session.finished or not session.turn_starts:
            return None
        start = session.turn_starts.pop()
        del session.history[start:]
        session.msg_count = max(0, session.msg_count - 1)
        return next(
            (m["content"] for m in reversed(session.history) if m["role"] == "assistant"),
            None,
        )

    def get_report(self, session_id: str) -> str | None:
        s = self._sessions.get(session_id)
        return s.report_text if s else None


store = AgentStore()


async def _call_llm(messages: list[dict]) -> str:
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                settings.CLOUD_RU_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.CLOUD_RU_API_KEY}",
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
            data = r.json()
            return data["choices"][0]["message"]["content"]
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        raise LLMUnavailableError(str(e)) from e
    except (KeyError, IndexError, ValueError) as e:
        raise LLMUnavailableError(f"unexpected LLM response shape: {e}") from e
