"""Admin statistics and status handlers."""

from __future__ import annotations

from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from config import get_settings
from db_session import get_db
from models.crud import (
    count_active_users_on_date,
    count_active_users_since,
    count_approved_users,
    count_approved_users_on_date,
    count_awaiting_verification_users,
    count_new_users_on_date,
    count_total_users,
)

settings = get_settings()


async def show_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query=None,
    period: str = "all",
    *,
    get_db_fn=get_db,
    count_new_users_fn=count_new_users_on_date,
    count_approved_today_fn=count_approved_users_on_date,
    count_active_today_fn=count_active_users_on_date,
    count_awaiting_fn=count_awaiting_verification_users,
    count_total_fn=count_total_users,
    count_approved_fn=count_approved_users,
    datetime_module=datetime,
) -> None:
    if str(update.effective_user.id) != settings.ADMIN_CHAT_ID:
        return

    today = datetime_module.now().date()

    with get_db_fn() as db:
        if period == "today":
            new_today = count_new_users_fn(db, today)
            approved_today = count_approved_today_fn(db, today)
            active_today = count_active_today_fn(db, today)
            awaiting = count_awaiting_fn(db)
            stats_text = (
                "📊 *Статистика за сегодня*\n\n"
                f"➕ Новых: *{new_today}*\n"
                f"🏃‍♂️ Активных: *{active_today}*\n"
                f"✅ Одобрено: *{approved_today}*\n"
                f"⏳ Ожидает: *{awaiting}*"
            )
        else:
            total = count_total_fn(db)
            approved = count_approved_fn(db)
            awaiting = count_awaiting_fn(db)
            stats_text = (
                "📊 *Статистика за все время*\n\n"
                f"👤 Всего: *{total}*\n"
                f"✅ Одобрено: *{approved}*\n"
                f"⏳ Ожидает: *{awaiting}*"
            )

    if query:
        await query.edit_message_text(
            stats_text,
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="admin_stats")]]
            ),
        )
    else:
        await update.message.reply_text(stats_text, parse_mode="MarkdownV2")


async def show_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query=None,
    *,
    count_total_fn=count_total_users,
    count_active_since_fn=count_active_users_since,
    get_db_fn=get_db,
    datetime_module=datetime,
    timedelta_cls=timedelta,
) -> None:
    if str(update.effective_user.id) != settings.ADMIN_CHAT_ID:
        return

    now = datetime_module.now()
    since = now - timedelta_cls(hours=24)

    with get_db_fn() as db:
        total_users = count_total_fn(db)
        active_users = count_active_since_fn(db, since)

    status_text = (
        "📈 Статус системы\n"
        f"Обновлено: {now.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"🕒 Активны за 24 часа: {active_users}"
    )

    if query:
        await query.message.reply_text(status_text)
    else:
        await update.message.reply_text(status_text)


async def daily_stats_job(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    count_new_users_fn=count_new_users_on_date,
    count_approved_users_fn=count_approved_users_on_date,
    get_db_fn=get_db,
    datetime_module=datetime,
    timedelta_cls=timedelta,
) -> None:
    yesterday = (datetime_module.now() - timedelta_cls(days=1)).date()
    safe_date = escape_markdown(yesterday.strftime("%d.%m.%Y"), version=2)
    with get_db_fn() as db:
        new_yesterday = count_new_users_fn(db, yesterday)
        approved_yesterday = count_approved_users_fn(db, yesterday)
    report_text = (
        "🗓️ *Отчет за {date}*\n\n➕ Новых: *{new}*\n✅ Одобрено: *{approved}*"
    ).format(
        date=safe_date,
        new=new_yesterday,
        approved=approved_yesterday,
    )
    await context.bot.send_message(
        chat_id=settings.ADMIN_CHAT_ID,
        text=report_text,
        parse_mode="MarkdownV2",
    )


__all__ = ["show_stats", "show_status", "daily_stats_job"]
