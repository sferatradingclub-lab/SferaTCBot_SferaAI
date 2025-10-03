from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from config import (
    logger, ADMIN_CHAT_ID, WELCOME_IMAGE_ID, TRAINING_IMAGE_ID,
    PSYCHOLOGIST_IMAGE_ID, CHATGPT_IMAGE_ID, SUPPORT_IMAGE_ID
)
from keyboards import (
    get_main_menu_keyboard, get_channel_keyboard, get_training_keyboard,
    get_psychologist_keyboard, get_chatgpt_keyboard
)
from db_session import get_db
from models.crud import get_user, create_user, update_user_last_seen
from services.chatgpt_service import get_chatgpt_response

# Импортируем обработчики из других модулей, чтобы передать им управление
from .admin_handlers import handle_admin_message
from .verification_handlers import start_verification_process, handle_id_submission, handle_support_message


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    with get_db() as db:
        db_user = get_user(db, user.id)

        if not db_user:
            logger.info(f"Новый пользователь: {user.id} ({user.full_name}) @{user.username}")
            db_user = create_user(db, {'id': user.id, 'username': user.username, 'full_name': user.full_name})

            user_fullname = escape_markdown(user.full_name or "Имя не указано", version=2)
            user_username = f"@{escape_markdown(user.username, version=2)}" if user.username else "Нет"
            admin_message = (f"👋 Новый пользователь\\!\n\nИмя: {user_fullname}\nUsername: {user_username}\nID: `{user.id}`")
            try:
                await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message, parse_mode='MarkdownV2')
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление о новом пользователе админу: {e}")

        if db_user and db_user.is_banned:
            return

        update_user_last_seen(db, user.id)

        payload = " ".join(context.args)
        if payload == "trial_completed":
            await start_verification_process(update, context)
            return
        
    await update.message.reply_photo(
        photo=WELCOME_IMAGE_ID,
        caption=(
            f"Привет, {user.first_name}!\n\n"
            "Добро пожаловать в экосистему SferaTC. Здесь ты найдешь все для успешного старта в трейдинге.\n\n"
            "Чтобы быть в курсе всех обновлений, подпишись на наш основной канал!"
        ),
        reply_markup=get_channel_keyboard()
    )
    await update.message.reply_text(
        "Выберите действие в меню ниже:",
        reply_markup=get_main_menu_keyboard(user.id)
    )
async def show_training_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_db() as db:
        db_user = get_user(db, update.effective_user.id)
        is_approved = db_user.is_approved if db_user else False

    caption = "Наше бесплатное обучение проходит в специальном чат-боте на платформе ChatGPT."
    text = "Ты уже получил доступ к полному курсу!"
    
    if is_approved:
        await update.message.reply_text(text, reply_markup=get_training_keyboard(is_approved))
    else:
        await update.message.reply_photo(photo=TRAINING_IMAGE_ID, caption=caption, reply_markup=get_training_keyboard(is_approved))

async def show_psychologist_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_photo(photo=PSYCHOLOGIST_IMAGE_ID, caption="Наш ИИ-психолог поможет справиться со стрессом в трейдинге.", reply_markup=get_psychologist_keyboard())

async def show_chatgpt_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начинает сессию с LLM через OpenRouter."""
    context.user_data['state'] = 'chatgpt_active'
    context.user_data['chat_history'] = [{"role": "system", "content": "You are a helpful assistant."}]
    
    await update.message.reply_text(
        "Вы начали диалог с ИИ-ассистентом. Просто отправьте ваше сообщение. "
        "Чтобы закончить, нажмите кнопку ниже или введите /stop_chat.",
        reply_markup=get_chatgpt_keyboard()
    )

async def stop_chatgpt_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Завершает сессию с LLM и возвращает в главное меню."""
    context.user_data.pop('state', None)
    context.user_data.pop('chat_history', None)
    
    await update.message.reply_text(
        "Диалог завершен. Вы вернулись в главное меню.",
        reply_markup=get_main_menu_keyboard(update.effective_user.id)
    )

async def show_support_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['state'] = 'awaiting_support_message'
    await update.message.reply_photo(photo=SUPPORT_IMAGE_ID, caption="Слушаю твой вопрос. Просто отправь его следующим сообщением (можно текст, фото, видео или голосовое).")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Это бот образовательной экосистемы SferaTC. Используйте меню для навигации по разделам.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    with get_db() as db:
        db_user = get_user(db, user.id)

        if not db_user:
            db_user = create_user(db, {'id': user.id, 'username': user.username, 'full_name': user.full_name})

        if db_user and db_user.is_banned:
            return

        update_user_last_seen(db, user.id)
    
    admin_state = context.user_data.get('admin_state')
    user_state = context.user_data.get('state')
    
    if user_state == 'chatgpt_active':
        if update.message.text == "Закончить диалог":
            await stop_chatgpt_session(update, context)
            return

        history = context.user_data.get('chat_history', [])
        history.append({"role": "user", "content": update.message.text})
        
        if len(history) > 11:
            context.user_data['chat_history'] = [history[0]] + history[-10:]
        else:
            context.user_data['chat_history'] = history

        response_text = await get_chatgpt_response(context.user_data['chat_history'])
        
        if response_text and response_text.strip():
            context.user_data['chat_history'].append({"role": "assistant", "content": response_text})
            await update.message.reply_text(response_text, reply_markup=get_chatgpt_keyboard())
        else:
            logger.warning("Модель вернула пустой или некорректный ответ.")
            await update.message.reply_text(
                "Мне не удалось сгенерировать ответ. Попробуйте переформулировать ваш запрос.", 
                reply_markup=get_chatgpt_keyboard()
            )

    elif str(user.id) == ADMIN_CHAT_ID and admin_state:
        await handle_admin_message(update, context)
    elif user_state == 'awaiting_support_message':
        await handle_support_message(update, context)
    elif db_user and db_user.awaiting_verification:
        await handle_id_submission(update, context)
