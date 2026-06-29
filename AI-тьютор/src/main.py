import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from src.config import Config
from src.db.database import init_db, close_db
from src.handlers.registration import (
    start_command, ask_name, ask_audience, ask_goal, level_test_answer, finish_test,
    ASK_NAME, ASK_AUDIENCE, ASK_GOAL, LEVEL_TEST
)
from src.handlers.dialog import (
    new_dialog_command, scenario_selected, handle_message, end_dialog
)
from src.handlers.profile import profile_command, stats_command
from src.handlers.payment import (
    start_payment_command, buy_monthly_command
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SpeakBuddyBot:
    """Telegram bot for English conversation practice with Claude AI."""

    def __init__(self) -> None:
        """Initialize bot."""
        self.application: Application | None = None

    async def post_init(self, application: Application) -> None:
        """Initialize database on bot startup."""
        logger.info("Initializing database...")
        await init_db()
        logger.info("✅ Database initialized successfully")

    async def post_stop(self, application: Application) -> None:
        """Close database on bot shutdown."""
        logger.info("Closing database connections...")
        await close_db()
        logger.info("✅ Database closed")

    def build_app(self) -> Application:
        """Build and configure the Telegram bot application.

        Returns:
            Configured Application instance
        """
        config = Config()
        self.application = (
            Application.builder()
            .token(config.get_telegram_token)
            .post_init(self.post_init)
            .post_stop(self.post_stop)
            .build()
        )

        registration_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start_command)],
            states={
                ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
                ASK_AUDIENCE: [CallbackQueryHandler(ask_audience)],
                ASK_GOAL: [CallbackQueryHandler(ask_goal)],
                LEVEL_TEST: [CallbackQueryHandler(level_test_answer)],
            },
            fallbacks=[CommandHandler("start", start_command)],
        )

        self.application.add_handler(registration_conv_handler)
        self.application.add_handler(CommandHandler("new", new_dialog_command))
        self.application.add_handler(CommandHandler("profile", profile_command))
        self.application.add_handler(CommandHandler("stats", stats_command))
        self.application.add_handler(CommandHandler("premium", start_payment_command))
        self.application.add_handler(CommandHandler("buy_monthly", buy_monthly_command))
        self.application.add_handler(CommandHandler("end", end_dialog))

        self.application.add_handler(CallbackQueryHandler(scenario_selected, pattern="^scenario_"))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )

        return self.application

    def run(self) -> None:
        """Start the bot with polling."""
        logger.info("🤖 Starting SpeakBuddy bot...")
        app = self.build_app()
        asyncio.run(app.run_polling())
        logger.info("🛑 Bot stopped")


if __name__ == "__main__":
    try:
        bot = SpeakBuddyBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
