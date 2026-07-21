# app/bot/auth.py
import logging

from telegram import Update

log = logging.getLogger(__name__)


def is_authorized(update: Update, allowed_user_id: int) -> bool:
    user = update.effective_user
    if user is not None and user.id == allowed_user_id:
        return True
    log.warning("ignored update from unauthorized user %s", user.id if user else None)
    return False
