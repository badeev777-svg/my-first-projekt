# app/bot/handlers/project.py
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.bot.auth import is_authorized
from app.config import Settings
from app.state import StateStore


def _project_list_text(projects: dict[str, str]) -> str:
    names = "\n".join(f"- {name}" for name in sorted(projects))
    return f"Доступные проекты:\n{names}"


async def cmd_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not is_authorized(update, settings.allowed_user_id):
        return
    state: StateStore = context.bot_data["state"]
    projects = await state.list_all_projects(settings.projects)
    await update.message.reply_text(_project_list_text(projects))


async def cmd_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not is_authorized(update, settings.allowed_user_id):
        return

    state: StateStore = context.bot_data["state"]
    projects = await state.list_all_projects(settings.projects)

    args = context.args
    if not args or args[0] not in projects:
        await update.message.reply_text(
            f"Укажи один из доступных проектов:\n{_project_list_text(projects)}"
        )
        return

    project = args[0]
    await state.set_active_project(update.effective_user.id, project)
    await update.message.reply_text(f"Активный проект: {project}")


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not is_authorized(update, settings.allowed_user_id):
        return

    state: StateStore = context.bot_data["state"]
    project = await state.get_active_project(update.effective_user.id)
    if project is None:
        await update.message.reply_text("Сначала выбери проект: /projects")
        return

    await state.delete_session_id(project)
    await update.message.reply_text(
        f"Сессия для {project} сброшена. Следующее сообщение начнёт новый разговор."
    )


def register(app: Application) -> None:
    app.add_handler(CommandHandler("projects", cmd_projects))
    app.add_handler(CommandHandler("project", cmd_project))
    app.add_handler(CommandHandler("reset", cmd_reset))
