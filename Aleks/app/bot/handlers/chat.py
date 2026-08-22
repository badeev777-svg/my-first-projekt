# app/bot/handlers/chat.py
import asyncio
import logging

import tenacity
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from app.agent_runner import run_turn
from app.bot.auth import is_authorized
from app.config import Settings
from app.confirmation import ConfirmationBridge
from app.new_project import handle_new_project, parse_new_project_trigger
from app.state import StateStore

log = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT = 4096

# Prepended to the first message of a fresh session only (session_id is None).
# The deployed agent runs with setting_sources=[] (see agent_runner.py), so it
# never sees the local Superpowers skills (brainstorming/writing-plans/etc.) --
# this inlines their gist as plain prompt text instead of wiring up real skill
# discovery, which would require reintroducing settings-file loading and
# re-auditing the can_use_tool confirmation bypass risk that setting_sources=[]
# exists to avoid.
NEW_SESSION_PREAMBLE = (
    "Прежде чем писать код: если задача про новый проект/фичу и цель или объём "
    "неочевидны -- сначала кратко уточни их вопросом, не начинай сразу кодить. "
    "Затем набросай короткий план шагов и покажи его. После этого реализуй план "
    "шаг за шагом. Перед тем как сказать, что готово -- проверь результат "
    "(тесты/запуск), а не просто заяви об успехе.\n\n---\n\n"
)

# Retry a run_turn() call a few times with exponential backoff before
# falling back to the user-facing error message. Covers transient
# Anthropic API errors (rate limits, network blips) per the spec. Module
# attributes (not baked into a module-level Retrying instance) so tests can
# monkeypatch them to keep test runs fast.
_RETRY_ATTEMPTS = 3
_RETRY_WAIT_SECONDS = 1.0

# Billing/insufficient-funds errors (e.g. Polza.ai's "402 Недостаточно
# средств") are not transient -- retrying them just re-bills the same
# failing call up to _RETRY_ATTEMPTS times for no benefit. Matched by
# substring against str(exc) since the SDK surfaces these as generic
# Exceptions, not a dedicated billing error type.
_BILLING_ERROR_MARKERS = ("402", "insufficient", "недостаточно средств")


def _is_billing_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(marker.lower() in text for marker in _BILLING_ERROR_MARKERS)


def _describe_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "Bash":
        return f"Bash: {tool_input.get('command', '')}"
    if tool_name in ("Write", "Edit"):
        return f"{tool_name}: {tool_input.get('file_path', '')}"
    return f"{tool_name}: {tool_input}"


async def on_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if update.message is None or not is_authorized(update, settings.allowed_user_id):
        return
    user = update.effective_user

    state: StateStore = context.bot_data["state"]

    new_project_name = parse_new_project_trigger(update.message.text)
    if new_project_name is not None:
        try:
            reply = await handle_new_project(new_project_name, user.id, settings, state)
        except Exception:
            log.exception("new-project trigger failed for user %s", user.id)
            await update.message.reply_text("Не получилось выполнить запрос, попробуй позже.")
            return
        await update.message.reply_text(reply)
        return

    project = await state.get_active_project(user.id)
    if project is None:
        await update.message.reply_text("Сначала выбери проект: /projects")
        return

    locks: dict[str, asyncio.Lock] = context.bot_data["project_locks"]
    lock = locks.setdefault(project, asyncio.Lock())
    if lock.locked():
        await update.message.reply_text(
            f"Ещё работаю над предыдущим запросом для {project}, подожди."
        )
        return

    async with lock:
        bridge: ConfirmationBridge = context.bot_data["confirmation_bridge"]
        chat_id = update.effective_chat.id

        async def send_confirmation_prompt(
            correlation_id: str, tool_name: str, tool_input: dict
        ) -> None:
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("✅ Разрешить", callback_data=f"{correlation_id}:yes"),
                        InlineKeyboardButton("❌ Отклонить", callback_data=f"{correlation_id}:no"),
                    ]
                ]
            )
            text = f"Подтверди действие:\n{_describe_tool(tool_name, tool_input)}"
            if len(text) > TELEGRAM_MESSAGE_LIMIT:
                suffix = "...(обрезано)"
                text = text[: TELEGRAM_MESSAGE_LIMIT - len(suffix)] + suffix
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard,
            )

        async def on_confirmation_timeout() -> None:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Действие отменено по таймауту ожидания подтверждения.",
            )

        async def on_text(text: str) -> None:
            for i in range(0, len(text), TELEGRAM_MESSAGE_LIMIT):
                await context.bot.send_message(
                    chat_id=chat_id, text=text[i : i + TELEGRAM_MESSAGE_LIMIT]
                )

        merged_projects = await state.list_all_projects(settings.projects)
        project_path = merged_projects.get(project)
        if project_path is None:
            await update.message.reply_text(
                "Проект больше не настроен, выбери заново: /projects"
            )
            return

        session_id = await state.get_session_id(project)
        prompt = update.message.text
        if session_id is None:
            prompt = NEW_SESSION_PREAMBLE + prompt

        async def on_session_id(new_session_id: str) -> None:
            nonlocal session_id
            session_id = new_session_id
            await state.set_session_id(project, new_session_id)

        retrying = tenacity.AsyncRetrying(
            stop=tenacity.stop_after_attempt(_RETRY_ATTEMPTS),
            wait=tenacity.wait_exponential(multiplier=_RETRY_WAIT_SECONDS, max=10),
            retry=tenacity.retry_if_exception(lambda exc: not _is_billing_error(exc)),
            reraise=True,
        )

        async def _run_turn_with_timeout() -> str | None:
            return await asyncio.wait_for(
                run_turn(
                    prompt=prompt,
                    project_path=project_path,
                    session_id=session_id,
                    confirmation_bridge=bridge,
                    send_confirmation_prompt=send_confirmation_prompt,
                    on_text=on_text,
                    on_confirmation_timeout=on_confirmation_timeout,
                    on_session_id=on_session_id,
                    model=settings.model,
                    effort=settings.agent_effort,
                    max_budget_usd=settings.max_turn_budget_usd,
                ),
                timeout=settings.run_turn_timeout_seconds,
            )

        try:
            new_session_id = await retrying(_run_turn_with_timeout)
        except Exception:
            log.exception("agent turn failed for project %s", project)
            await update.message.reply_text("Не получилось выполнить запрос, попробуй позже.")
            return

        if new_session_id:
            await state.set_session_id(project, new_session_id)


def register(app: Application) -> None:
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_message))
