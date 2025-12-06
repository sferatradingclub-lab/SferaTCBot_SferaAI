"""Payment handlers for subscription purchase."""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from handlers.decorators import user_bootstrap, handle_errors
from db_session import get_db
from models.subscription_crud import create_payment
from models.payment import PaymentMethod, PaymentStatus
from services.cryptobot_payment import CryptoBotClient  # Changed from Heleket
from services.promo_service import validate_promo_code, calculate_discounted_price
from services.subscription_service import format_usage_stats

logger = logging.getLogger(__name__)

# Conversation states
CHOOSING_PRODUCT, CHOOSING_TIER, ENTERING_PROMO, CONFIRMING_PAYMENT = range(4)

# Constants
PRO_PRICE = 24.99
PRO_CURRENCY = "USDT"


@handle_errors
@user_bootstrap
async def show_payment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user, is_new_user) -> int:
    """Main payment menu - choose what to pay for."""
    keyboard = [
        [InlineKeyboardButton("🎙️ SferaAI", callback_data="pay_sferaai")],
        # Future options can be added here:
        # [InlineKeyboardButton("📊 Скринер", callback_data="pay_screener")],
    ]
    
    message_text = (
        "💳 <b>Оплата подписки</b>\n\n"
        "Выберите, что хотите оплатить:"
    )
    
    if update.message:
        await update.message.reply_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    elif update.callback_query:
        await update.callback_query.message.edit_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    
    return CHOOSING_PRODUCT


async def show_sferaai_tiers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show SferaAI subscription tiers."""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton(f"💎 Pro - ${PRO_PRICE}/мес", callback_data="tier_pro")],
        [InlineKeyboardButton("« Назад", callback_data="back_to_menu")],
    ]
    
    await query.edit_message_text(
        "🎙️ <b>SferaAI Subscription</b>\n\n"
        f"💎 <b>Pro (${PRO_PRICE}/месяц)</b>\n"
        "✅ Неограниченные сессии\n"
        "✅ Безлимитное время разговора\n"
        "✅ Доступ к базе знаний\n"
        "✅ Веб-поиск\n"
        "✅ Приоритетная поддержка\n\n"
        "Выберите тариф:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return CHOOSING_TIER


async def ask_for_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask if user has promo code."""
    query = update.callback_query
    await query.answer()
    
    # Store selected tier
    context.user_data['selected_tier'] = 'pro'
    context.user_data['original_price'] = PRO_PRICE
    
    keyboard = [
        [InlineKeyboardButton("✅ У меня есть промокод", callback_data="has_promo")],
        [InlineKeyboardButton("❌ Продолжить без промокода", callback_data="no_promo")],
    ]
    
    await query.edit_message_text(
        f"💎 <b>Pro подписка - ${PRO_PRICE}</b>\n\n"
        "У вас есть промокод?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return ENTERING_PROMO


async def prompt_promo_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user to enter promo code."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🎟️ Введите промокод:\n\n"
        "(Отправьте промокод в следующем сообщении)"
    )
    
    return ENTERING_PROMO


async def process_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validate and apply promo code."""
    promo_code = update.message.text.strip().upper()
    user_id = update.effective_user.id
    
    # Validate promo code
    valid, discount, message = await validate_promo_code(promo_code, user_id, "pro")
    
    if valid:
        context.user_data['promo_code'] = promo_code
        context.user_data['discount'] = discount
        
        original_price = context.user_data['original_price']
        final_price = calculate_discounted_price(original_price, discount)
        
        context.user_data['final_price'] = final_price
        
        await update.message.reply_text(
            f"✅ Промокод применен!\n\n"
            f"Скидка: {discount}%\n"
            f"Цена: <s>${original_price}</s> → <b>${final_price}</b>",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            f"{message}\n\n"
            "Попробуйте другой код или продолжите без промокода: /skip_promo",
            parse_mode="HTML"
        )
        return ENTERING_PROMO
    
    return await initiate_cryptobot_payment(update, context)


async def skip_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip promo code entry."""
    context.user_data['promo_code'] = None
    context.user_data['discount'] = 0
    context.user_data['final_price'] = context.user_data['original_price']
    
    if update.message:
        return await initiate_cryptobot_payment(update, context)
    else:
        query = update.callback_query
        await query.answer()
        context._update = Update(update_id=update.update_id, message=query.message)
        return await initiate_cryptobot_payment(context._update, context)


async def initiate_cryptobot_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Create CryptoBot payment invoice."""
    user_id = update.effective_user.id
    tier = context.user_data.get('selected_tier', 'pro')
    final_price = context.user_data.get('final_price', PRO_PRICE)
    promo_code = context.user_data.get('promo_code')
    
    # Create CryptoBot invoice
    cryptobot = CryptoBotClient()
    
    try:
        invoice_data = await cryptobot.create_invoice(
            amount=final_price,
            currency=PRO_CURRENCY,
            description=f"Sfera AI Pro subscription - {tier}",
            user_id=user_id,
            tier=tier,
            promo_code=promo_code
        )
        
        # Save payment to DB
        with get_db() as db:
            db_payment = create_payment(
                db,
                user_id=user_id,
                amount=final_price,
                currency=PRO_CURRENCY,
                method=PaymentMethod.CRYPTO,
                tier=tier,
                heleket_payment_id=invoice_data['invoice_id'],  # Reusing field
                promo_code=promo_code
            )
        
        # Send payment details to user
        keyboard = [
            [InlineKeyboardButton("💳 Оплатить", url=invoice_data['pay_url'])],
            [InlineKeyboardButton("❌ Отменить", callback_data="cancel_payment")]
        ]
        
        message_text = (
            f"💳 <b>Оплата подписки Pro</b>\n\n"
            f"Сумма: <b>${final_price}</b>\n"
            f"Валюта: <b>{PRO_CURRENCY}</b>\n\n"
            f"Нажмите кнопку ниже для оплаты через @CryptoBot:\n\n"
            f"⏱ Инвойс действителен 24 часа\n\n"
            f"После оплаты подписка активируется автоматически."
        )
        
        if update.message:
            await update.message.reply_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        else:
            await update.effective_message.reply_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        
        logger.info(f"CryptoBot invoice created for user {user_id}: ${final_price} {PRO_CURRENCY}, invoice_id={invoice_data['invoice_id']}")
        
    except Exception as e:
        logger.error(f"Failed to create CryptoBot invoice for user {user_id}: {e}")
        error_text = (
            "❌ Ошибка создания платежа.\n\n"
            "Попробуйте позже или свяжитесь с поддержкой: /support"
        )
        if update.message:
            await update.message.reply_text(error_text)
        else:
            await update.effective_message.reply_text(error_text)
    
    return ConversationHandler.END


async def  cancel_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel payment process."""
    query = update.callback_query
    await query.answer("Платеж отменен")
    
    await query.edit_message_text(
        "❌ Платеж отменен.\n\n"
        "Вы можете вернуться к оплате в любое время: /subscribe"
    )
    
    return ConversationHandler.END


async def subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /subscribe command."""
    return await show_payment_menu(update, context)


# Build conversation handler
payment_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("subscribe", subscription_command),
        MessageHandler(filters.Regex("^💳 Оплатить подписку$"), show_payment_menu),
    ],
    states={
        CHOOSING_PRODUCT: [
            CallbackQueryHandler(show_sferaai_tiers, pattern="^pay_sferaai$"),
        ],
        CHOOSING_TIER: [
            CallbackQueryHandler(ask_for_promo_code, pattern="^tier_pro$"),
            CallbackQueryHandler(show_payment_menu, pattern="^back_to_menu$"),
        ],
        ENTERING_PROMO: [
            CallbackQueryHandler(prompt_promo_code_input, pattern="^has_promo$"),
            CallbackQueryHandler(skip_promo_code, pattern="^no_promo$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_promo_code),
            CommandHandler("skip_promo", skip_promo_code),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_payment, pattern="^cancel_payment$"),
        CommandHandler("cancel", cancel_payment),
    ],
    name="payment_conversation",
    persistent=False,
)


__all__ = ["payment_conversation", "subscription_command"]
