"""Handler for Sfera AI mini app."""

from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import get_settings
from handlers.decorators import user_bootstrap
from handlers.error_handler import handle_errors

settings = get_settings()


@handle_errors
@user_bootstrap
async def show_sfera_ai(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_user,
    is_new_user: bool,
) -> None:
    """Shows Sfera AI mini app with WebApp button."""
    
    if update.message is None:
        return
    
    mini_app_url = settings.WEBHOOK_URL or "http://localhost:8000"
    
    keyboard = [[
        InlineKeyboardButton(
            text="🤖 Открыть Sfera AI",
            web_app=WebAppInfo(url=mini_app_url)
        )
    ]]
    
    await update.message.reply_text(
        "🎙️ <b>Sfera AI - Голосовой AI-ассистент</b>\n\n"
        "Твой персональный помощник с памятью и базой знаний.\n\n"
        "✨ Голосовое общение в реальном времени\n"
        "🧠 Помнит всё, о чём вы говорили\n"
        "📚 Использует базу знаний SferaTC\n"
        "🔍 Может искать информацию в интернете\n\n"
        "Нажми кнопку ниже, чтобы начать:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


__all__ = ["show_sfera_ai"]
