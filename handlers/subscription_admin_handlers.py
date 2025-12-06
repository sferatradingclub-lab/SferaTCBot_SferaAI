"""Admin commands for subscription and promo code management."""

import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

from handlers.decorators import user_bootstrap, handle_errors
from db_session import get_db
from models.subscription_crud import (
    create_promo_code,
    get_all_promo_codes,
    deactivate_promo_code,
    count_subscriptions_by_tier,
    create_pro_subscription,
)
from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return str(user_id) == settings.ADMIN_CHAT_ID


@handle_errors
@user_bootstrap
async def create_promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user, is_new_user) -> None:
    """
    Create new promo code.
    
    Usage: /create_promo <CODE> <DISCOUNT%> [max_uses] [valid_days]
    Example: /create_promo SAVE20 20 100 30
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Только для администраторов")
        return
    
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "📝 Использование:\n"
            "/create_promo <КОД> <СКИДКА%> [макс_использований] [дней_действия]\n\n"
            "Примеры:\n"
            "• /create_promo SAVE20 20\n"
            "• /create_promo FIRST50 50 100 30\n"
            "• /create_promo VIP30 30 10"
        )
        return
    
    code = args[0].upper()
    
    try:
        discount = float(args[1])
        max_uses = int(args[2]) if len(args) > 2 else None
        valid_days = int(args[3]) if len(args) > 3 else None
        
        if discount <= 0 or discount > 100:
            await update.message.reply_text("❌ Скидка должна быть от 1 до 100%")
            return
        
        with get_db() as db:
            promo = create_promo_code(
                db,
                code=code,
                discount_percent=discount,
                created_by=user_id,
                max_uses=max_uses,
                valid_days=valid_days
            )
        
        expiry_info = f"до {promo.valid_until.strftime('%Y-%m-%d')}" if promo.valid_until else "бессрочно"
        uses_info = f"{max_uses} раз" if max_uses else "неограниченно"
        
        await update.message.reply_text(
            f"✅ <b>Промокод создан!</b>\n\n"
            f"🎟️ Код: <code>{code}</code>\n"
            f"💰 Скидка: {discount}%\n"
            f"🔢 Использований: {uses_info}\n"
            f"📅 Действует: {expiry_info}",
            parse_mode="HTML"
        )
        
        logger.info(f"Admin {user_id} created promo code: {code} ({discount}%)")
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат чисел")
    except Exception as e:
        logger.error(f"Error creating promo code: {e}")
        await update.message.reply_text(f"❌ Ошибка создания промокода: {str(e)}")


@handle_errors
@user_bootstrap
async def list_promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user, is_new_user) -> None:
    """List all promo codes."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Только для администраторов")
        return
    
    with get_db() as db:
        promos = get_all_promo_codes(db)
    
    if not promos:
        await update.message.reply_text("📋 Промокодов пока нет")
        return
    
    message_lines = ["📋 <b>Список промокодов:</b>\n"]
    
    for promo in promos[:20]:  # Limit to 20 to avoid message length issues
        status = "✅" if promo.is_active else "❌"
        expiry = promo.valid_until.strftime('%Y-%m-%d') if promo.valid_until else "∞"
        uses = f"{promo.current_uses}/{promo.max_uses}" if promo.max_uses else f"{promo.current_uses}/∞"
        
        message_lines.append(
            f"{status} <code>{promo.code}</code>\n"
            f"   💰 {promo.discount_percent}% | 🔢 {uses} | 📅 {expiry}\n"
        )
    
    if len(promos) > 20:
        message_lines.append(f"\n...и еще {len(promos) - 20} промокодов")
    
    await update.message.reply_text("".join(message_lines), parse_mode="HTML")


@handle_errors
@user_bootstrap
async def deactivate_promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user, is_new_user) -> None:
    """
    Deactivate promo code.
    
    Usage: /deactivate_promo <CODE>
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Только для администраторов")
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /deactivate_promo <КОД>")
        return
    
    code = context.args[0].upper()
    
    with get_db() as db:
        success = deactivate_promo_code(db, code)
    
    if success:
        await update.message.reply_text(f"✅ Промокод <code>{code}</code> деактивирован", parse_mode="HTML")
        logger.info(f"Admin {user_id} deactivated promo code: {code}")
    else:
        await update.message.reply_text(f"❌ Промокод <code>{code}</code> не найден", parse_mode="HTML")


@handle_errors
@user_bootstrap
async def subscription_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user, is_new_user) -> None:
    """Show subscription statistics."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Только для администраторов")
        return
    
    with get_db() as db:
        tier_counts = count_subscriptions_by_tier(db)
    
    free_count = tier_counts.get("free", 0)
    pro_count = tier_counts.get("pro", 0)
    total = free_count + pro_count
    
    pro_percentage = (pro_count / total * 100) if total > 0 else 0
    
    message = (
        f"📊 <b>Статистика подписок</b>\n\n"
        f"👥 Всего: {total}\n"
        f"🆓 Free: {free_count}\n"
        f"💎 Pro: {pro_count} ({pro_percentage:.1f}%)\n"
    )
    
    await update.message.reply_text(message, parse_mode="HTML")


@handle_errors
@user_bootstrap
async def grant_subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user, is_new_user) -> None:
    """
    Manually grant Pro subscription to user.
    
    Usage: /grant_sub <user_id> [days]
    Example: /grant_sub 123456789 30
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Только для администраторов")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Использование: /grant_sub <user_id> [дней]\n"
            "Пример: /grant_sub 123456789 30"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        days = int(context.args[1]) if len(context.args) > 1 else 30
        
        with get_db() as db:
            subscription = create_pro_subscription(
                db,
                user_id=target_user_id,
                duration_days=days,
                payment_id=None
            )
        
        expiry_date = subscription.expiry_date.strftime('%Y-%m-%d %H:%M') if subscription.expiry_date else "Никогда"
        
        await update.message.reply_text(
            f"✅ <b>Подписка выдана!</b>\n\n"
            f"👤 User ID: <code>{target_user_id}</code>\n"
            f"💎 Tier: Pro\n"
            f"⏰ Действует: {days} дней\n"
            f"📅 До: {expiry_date}",
            parse_mode="HTML"
        )
        
        # Try to notify user
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"🎉 <b>Вам выдана Pro подписка!</b>\n\n"
                    f"⏰ Действует: {days} дней\n"
                    f"📅 До: {expiry_date}\n\n"
                    f"Наслаждайтесь безлимитным доступом!"
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Could not notify user {target_user_id}: {e}")
        
        logger.info(f"Admin {user_id} granted Pro subscription to user {target_user_id} for {days} days")
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Используйте числа для user_id и дней")
    except Exception as e:
        logger.error(f"Error granting subscription: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


__all__ = [
    "create_promo_command",
    "list_promo_command",
    "deactivate_promo_command",
    "subscription_stats_command",
    "grant_subscription_command",
]
