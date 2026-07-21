# app/bot/handlers/project.py
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.bot.auth import is_authorized
from app.config import Settings
from app.state import StateStore


def _project_list_text(settings: Settings) -> str:
    names = "\n".join(f"- {name}" for name in sorted(settings.projects))
    return f"Доступные проекты:\n{names}"


async def cmd_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not is_authorized(update, settings.allowed_user_id):
        return
    await update.message.reply_text(_project_list_text(settings))


async def cmd_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not is_authorized(update, settings.allowed_user_id):
        return

    args = context.args
    if not args or args[0] not in settings.projects:
        await update.message.reply_text(
            f"Укажи один из доступных проектов:\n{_project_list_text(settings)}"
        )
        return

    project = args[0]
    state: StateStore = context.bot_data["state"]
    await state.set_active_project(update.effective_user.id, project)
    await update.message.reply_text(f"Активный проект: {project}")


def register(app: Application) -> None:
    app.add_handler(CommandHandler("projects", cmd_projects))
    app.add_handler(CommandHandler("project", cmd_project))
