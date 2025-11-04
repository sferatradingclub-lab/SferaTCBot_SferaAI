"""Admin broadcast utilities and handlers."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # для старых версий Python

from typing import AsyncGenerator, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from config import get_settings
from db_session import get_db
from models.crud import iter_broadcast_targets, create_scheduled_broadcast, get_scheduled_broadcast, get_scheduled_broadcasts_by_admin
from models.user import User  # Добавляем импорт модели User
from services.notifier import Notifier
from services.state_manager import StateManager
from handlers.states import AdminState
from handlers.calendar import create_calendar_keyboard, create_date_quick_select_keyboard

settings = get_settings()
logger = settings.logger


async def iter_broadcast_targets_optimized(
    db,
    *,
    chunk_size: int = 1000,
    batch_size: int = 100
) -> AsyncGenerator[list[int], None]:
    """
    Оптимизированный итератор ID пользователей для рассылки с пагинацией.
    
    Args:
        db: Сессия базы данных
        chunk_size: Размер чанка для загрузки из базы
        batch_size: Размер батча для отправки сообщений
    """
    admin_id: Optional[int] = None
    if settings.ADMIN_CHAT_ID is not None:
        try:
            admin_id = int(settings.ADMIN_CHAT_ID)
        except (TypeError, ValueError):
            admin_id = None

    query = db.query(User.user_id).filter(User.is_banned.is_(False))
    if admin_id is not None:
        query = query.filter(User.user_id != admin_id)

    current_batch = []
    for row in query.order_by(User.user_id).yield_per(chunk_size):
        user_id = getattr(row, "user_id", row[0])
        current_batch.append(user_id)
        
        if len(current_batch) >= batch_size:
            yield current_batch
            current_batch = []
    
    # Отправляем оставшиеся ID
    if current_batch:
        yield current_batch


async def prepare_broadcast_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.message
    if message is None:
        return

    state_manager = StateManager(context)
    state_manager.set_admin_state(AdminState.BROADCAST_AWAITING_CONFIRMATION)
    context.user_data["broadcast_message_id"] = message.message_id
    
    # Сохраняем информацию о сообщении, включая медиа-контент
    original_text = getattr(message, 'text', None) or getattr(message, 'caption', None)
    if original_text:
        context.user_data["broadcast_original_text"] = original_text

    # Проверяем наличие медиа-контента и сохраняем его данные
    if message.photo:  # Если это фото
        # Берем фото самого высокого качества (последний элемент в массиве)
        photo_file_id = message.photo[-1].file_id
        context.user_data["broadcast_photo_id"] = photo_file_id
        # Сохраняем подпись, если она есть
        if message.caption:
            context.user_data["broadcast_caption"] = message.caption
    elif message.video:  # Если это видео
        video_file_id = message.video.file_id
        context.user_data["broadcast_video_id"] = video_file_id
        if message.caption:
            context.user_data["broadcast_caption"] = message.caption
    elif message.document:  # Если это документ
        document_file_id = message.document.file_id
        context.user_data["broadcast_document_id"] = document_file_id
        if message.caption:
            context.user_data["broadcast_caption"] = message.caption
    elif message.audio:  # Если это аудио
        audio_file_id = message.audio.file_id
        context.user_data["broadcast_audio_id"] = audio_file_id
        if message.caption:
            context.user_data["broadcast_caption"] = message.caption
    elif message.voice:  # Если это голосовое сообщение
        voice_file_id = message.voice.file_id
        context.user_data["broadcast_voice_id"] = voice_file_id
        if message.caption:  # Для голосовых сообщений также может быть подпись
            context.user_data["broadcast_caption"] = message.caption

    await context.bot.copy_message(
        chat_id=settings.ADMIN_CHAT_ID,
        from_chat_id=settings.ADMIN_CHAT_ID,
        message_id=message.message_id,
    )

    # Кнопки для выбора типа отправки
    confirmation_keyboard = [
        [InlineKeyboardButton("✅ Да, отправить сейчас", callback_data="broadcast_send")],
        [InlineKeyboardButton("⏳ Отложенная отправка", callback_data="broadcast_schedule_later")],
        [InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel")],
    ]
    await message.reply_text(
        "Вот так будет выглядеть ваше сообщение. Все верно?",
        reply_markup=InlineKeyboardMarkup(confirmation_keyboard),
    )


async def send_broadcast_batch(
    bot,
    user_ids: list[int],
    admin_chat_id: str,
    message_id: int,
    semaphore: asyncio.Semaphore
) -> tuple[int, int, int]:
    """
    Отправляет сообщение батчу пользователей асинхронно.
    
    Args:
        bot: Экземпляр бота
        user_ids: Список ID пользователей для отправки
        admin_chat_id: ID чата администратора
        message_id: ID сообщения для копирования
        semaphore: Семафор для ограничения параллелизма
        
    Returns:
        tuple: (успешно отправлено, заблокировано, ошибки)
    """
    async with semaphore:
        success = 0
        blocked = 0
        error = 0
        
        # Создаем задачи для параллельной отправки
        tasks = []
        for user_id in user_ids:
            task = asyncio.create_task(_send_single_message(bot, user_id, admin_chat_id, message_id))
            tasks.append(task)
        
        # Ждем выполнения всех задач в батче
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты
        for result in results:
            if isinstance(result, Exception):
                # Если была ошибка при отправке
                error += 1
            elif result == "blocked":
                blocked += 1
            elif result == "success":
                success += 1
        
        return success, blocked, error


async def _send_single_message(bot, user_id: int, admin_chat_id: str, message_id: int) -> str:
    """
    Отправляет одно сообщение пользователю с обработкой ошибок.
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        admin_chat_id: ID чата администратора
        message_id: ID сообщения для копирования
        
    Returns:
        str: Статус отправки ("success", "blocked", или исключение)
    """
    try:
        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=admin_chat_id,
            message_id=message_id,
        )
        return "success"
    except TelegramError as err:
        if "bot was blocked" in err.message or "user is deactivated" in err.message:
            return "blocked"
        else:
            # Логируем ошибку, но не возвращаем исключение, чтобы не прерывать весь батч
            logger.warning("Ошибка рассылки пользователю %s: %s", user_id, err)
            return "error"


async def broadcast_confirmation_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    command = query.data

    if command == "broadcast_send":
        state_manager = StateManager(context)
        state_manager.reset_admin_state()
        await query.edit_message_text("Начинаю рассылку... Оповещу по завершении.")
        context.job_queue.run_once(run_broadcast, 0)
    elif command == "broadcast_schedule_later":
        # Переходим в состояние ожидания выбора даты
        state_manager = StateManager(context)
        state_manager.set_admin_state(AdminState.BROADCAST_SCHEDULE_AWAITING_DATE)
        # Сохраняем ID сообщения для отложенной отправки
        context.user_data["scheduled_broadcast_message_id"] = context.user_data.get("broadcast_message_id")
        # Сохраняем оригинальный текст, если он есть
        original_text = context.user_data.get("broadcast_original_text")
        if original_text:
            context.user_data["scheduled_broadcast_original_text"] = original_text
        
        # Сохраняем медиа-данные, если они есть
        photo_id = context.user_data.get("broadcast_photo_id")
        if photo_id:
            context.user_data["scheduled_broadcast_photo_id"] = photo_id
        video_id = context.user_data.get("broadcast_video_id")
        if video_id:
            context.user_data["scheduled_broadcast_video_id"] = video_id
        document_id = context.user_data.get("broadcast_document_id")
        if document_id:
            context.user_data["scheduled_broadcast_document_id"] = document_id
        audio_id = context.user_data.get("broadcast_audio_id")
        if audio_id:
            context.user_data["scheduled_broadcast_audio_id"] = audio_id
        voice_id = context.user_data.get("broadcast_voice_id")
        if voice_id:
            context.user_data["scheduled_broadcast_voice_id"] = voice_id
        caption = context.user_data.get("broadcast_caption")
        if caption:
            context.user_data["scheduled_broadcast_caption"] = caption
        
        # Показываем кнопки выбора даты
        keyboard = create_date_quick_select_keyboard()
        await query.edit_message_text("Выберите дату для отправки рассылки:", reply_markup=keyboard)
    elif command == "broadcast_cancel":
        state_manager = StateManager(context)
        state_manager.reset_admin_state()
        await query.edit_message_text("Рассылка отменена.")
        context.user_data.pop("broadcast_message_id", None)


async def run_broadcast(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    iter_targets=iter_broadcast_targets_optimized,  # Используем оптимизированную версию
    get_db_fn=None,
    asyncio_module=None,
) -> None:
    if get_db_fn is None:
        from handlers import admin_handlers as admin_module

        get_db_fn = admin_module.get_db
    if asyncio_module is None:
        from handlers import admin_handlers as admin_module

        asyncio_module = admin_module.asyncio
    admin_user_data = context.application.user_data.get(int(settings.ADMIN_CHAT_ID), {})
    message_id_to_send = admin_user_data.pop("broadcast_message_id", None)
    notifier = Notifier(context.bot)

    if not message_id_to_send:
        await notifier.send_admin_notification("❌ Ошибка: не найдено сообщение для рассылки.")
        return

    success, blocked, error = 0, 0, 0
    total_targets = 0
    logger.info("Начинаю рассылку сообщений.")

    # Ограничиваем количество одновременных запросов к API Telegram
    semaphore = asyncio.Semaphore(20)  # Максимум 20 одновременных отправок

    with get_db_fn() as db:
        # Используем оптимизированный итератор с батчингом
        async for user_batch in iter_targets(db):
            total_targets += len(user_batch)
            # Отправляем батч асинхронно
            batch_success, batch_blocked, batch_error = await send_broadcast_batch(
                context.bot,
                user_batch,
                settings.ADMIN_CHAT_ID,
                message_id_to_send,
                semaphore
            )
            success += batch_success
            blocked += batch_blocked
            error += batch_error

    logger.info("Рассылка завершена. Всего получателей: %s", total_targets)

    title = escape_markdown("Рассылка завершена!", version=2)
    report_text = (
        f"✅ *{title}*\n\n"
        f"• Успешно: *{success}*\n"
        f"• Заблокировали: *{blocked}*\n"
        f"• Ошибки: *{error}*"
    )
    await notifier.send_admin_notification(
        report_text,
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ В админку", callback_data="admin_main")]]
        ),
    )


__all__ = [
    "prepare_broadcast_message",
    "broadcast_confirmation_handler",
    "handle_calendar_callback",
    "handle_scheduled_broadcast_date_selection",
    "handle_scheduled_broadcast_time_input",
    "handle_scheduled_broadcast_confirmation",
    "handle_scheduled_broadcasts_list",
    "handle_scheduled_broadcast_view",
    "handle_broadcast_edit_text_request",
    "handle_broadcast_edit_datetime_request",
    "handle_broadcast_delete_request",
    "handle_broadcast_delete_confirm",
    "handle_broadcast_edit_text",
    "handle_broadcast_edit_datetime",
    "run_broadcast",
]


async def handle_calendar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback-запросов от календаря."""
    logger.info("Начало обработки календарного callback-запроса")
    query = update.callback_query
    if query is None:
        logger.warning("Получен callback_query равный None")
        return

    await query.answer()
    command = query.data
    logger.info(f"Получена календарная команда: {command}")

    # Проверяем, что пользователь находится в состоянии планирования рассылки
    state_manager = StateManager(context)
    current_state = state_manager.get_admin_state()
    logger.info(f"Текущее состояние пользователя: {current_state}")
    if current_state != AdminState.BROADCAST_SCHEDULE_AWAITING_DATE:
        # Вместо просто return, логируем проблему
        logger.warning(f"Календарная команда {command} получена в состоянии {current_state}, ожидалось BROADCAST_SCHEDULE_AWAITING_DATE")
        return

    logger.info(f"Обработка команды {command} в состоянии BROADCAST_SCHEDULE_AWAITING_DATE")
    try:
        if command.startswith("calendar_select_"):
            logger.info("Обработка команды calendar_select_")
            # Выбрана дата, теперь нужно ввести время
            selected_date_str = command.replace("calendar_select_", "")
            context.user_data["scheduled_broadcast_date"] = selected_date_str

            # Преобразуем формат даты для отображения в русском формате
            from datetime import datetime as dt
            selected_date_obj = dt.strptime(selected_date_str, "%Y-%m-%d").date()
            day = selected_date_obj.day
            months_map = {
                1: "января", 2: "февраля", 3: "марта", 4: "апреля",
                5: "мая", 6: "июня", 7: "июля", 8: "августа",
                9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
            }
            month_name = months_map.get(selected_date_obj.month, selected_date_obj.month)
            formatted_date = f"{day} {month_name} {selected_date_obj.year}"

            # Проверяем текущее состояние, чтобы определить, создаем мы новую рассылку или редактируем существующую
            current_state = state_manager.get_admin_state()
            if current_state == AdminState.BROADCAST_EDIT_AWAITING_DATE:
                # Это изменение даты существующей рассылки
                context.user_data["new_broadcast_date"] = selected_date_str
                state_manager.set_admin_state(AdminState.BROADCAST_EDIT_AWAITING_TIME)
                await query.edit_message_text(f"Вы выбрали новую дату: {formatted_date}\n\nТеперь введите новое время в формате ЧЧ:ММ (24-часовой формат):")
            else:
                # Это создание новой рассылки
                state_manager.set_admin_state(AdminState.BROADCAST_SCHEDULE_AWAITING_TIME)
                await query.edit_message_text(f"Вы выбрали дату: {formatted_date}\n\nТеперь введите время в формате ЧЧ:ММ (24-часовой формат):")

        elif command.startswith("calendar_prev_month_") or command.startswith("calendar_next_month_"):
            logger.info("Обработка команды навигации по месяцам")
            # Навигация по месяцам
            if command.startswith("calendar_prev_month_"):
                date_str = command.replace("calendar_prev_month_", "")
            else:
                date_str = command.replace("calendar_next_month_", "")
            
            try:
                year, month = map(int, date_str.split("-"))
                from datetime import date as dt_date
                target_date = dt_date(year, month, 1)
                new_keyboard = create_calendar_keyboard(target_date)
                await query.edit_message_reply_markup(reply_markup=new_keyboard)
            except ValueError:
                await query.edit_message_text("Ошибка при обработке даты.")

        elif command == "calendar_expand":
            logger.info("Обработка команды calendar_expand")
            # Развернуть полный календарь
            current_date = datetime.now(ZoneInfo("Europe/Minsk")).date()
            calendar_keyboard = create_calendar_keyboard(current_date)
            logger.info(f"Создана клавиатура календаря для даты {current_date}")
            try:
                await query.edit_message_text("Выберите дату:", reply_markup=calendar_keyboard)
                logger.info("Сообщение с календарем успешно отредактировано")
            except Exception as e:
                logger.error(f"Ошибка при редактировании сообщения для calendar_expand: {e}", exc_info=True)
                # Если не удалось отредактировать сообщение, отправляем новое
                try:
                    # Пересоздаем календарь, так как в предыдущем блоке могла быть ошибка
                    from datetime import date as dt_date
                    current_date = dt_date.today()
                    calendar_keyboard = create_calendar_keyboard(current_date)
                    await context.bot.send_message(
                        chat_id=query.from_user.id,
                        text="Выберите дату:",
                        reply_markup=calendar_keyboard
                    )
                    logger.info("Новое сообщение с календарем успешно отправлено")
                except Exception as e2:
                    logger.error(f"Ошибка при отправке нового сообщения для calendar_expand: {e2}", exc_info=True)
    except Exception as e:
        logger.error(f"Ошибка в обработке календарного события {command}: {e}", exc_info=True)
        try:
            await query.edit_message_text("Произошла ошибка при обработке календаря. Попробуйте снова.")
        except Exception:
            # Если не удалось отредактировать сообщение, просто пропускаем
            pass


async def handle_scheduled_broadcast_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка выбора даты для отложенной рассылки."""
    # Эта функция будет вызываться из основного обработчика callback-запросов
    # при нахождении в состоянии BROADCAST_SCHEDULE_AWAITING_DATE
    pass  # Реализация будет в handle_calendar_callback


async def handle_scheduled_broadcast_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода времени для отложенной рассылки."""
    message = update.message
    if message is None:
        return

    state_manager = StateManager(context)
    current_state = state_manager.get_admin_state()
    if current_state != AdminState.BROADCAST_SCHEDULE_AWAITING_TIME:
        return

    time_input = message.text.strip()

    # Проверяем формат времени (ЧЧ:М)
    import re
    time_pattern = r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
    if not re.match(time_pattern, time_input):
        await message.reply_text("Неверный формат времени. Пожалуйста, введите время в формате ЧЧ:ММ (например, 14:30)")
        return

    # Добавляем 0 в начало, если нужно
    if len(time_input.split(':')[0]) == 1:
        time_input = '0' + time_input

    context.user_data["scheduled_broadcast_time"] = time_input

    # Получаем выбранную дату и время
    selected_date_str = context.user_data.get("scheduled_broadcast_date")
    selected_time_str = context.user_data.get("scheduled_broadcast_time")
    if not selected_date_str or not selected_time_str:
        await message.reply_text("Ошибка: дата или время не выбраны.")
        state_manager.reset_admin_state()
        return

    from datetime import datetime as dt
    try:
        # Объединяем выбранную дату и время
        selected_datetime_str = f"{selected_date_str} {selected_time_str}"
        scheduled_datetime = dt.strptime(selected_datetime_str, "%Y-%m-%d %H:%M")
        current_datetime = dt.now()
        if scheduled_datetime <= current_datetime:
            await message.reply_text("Ошибка: нельзя запланировать рассылку на прошедшее время. Пожалуйста, выберите будущую дату и время.")
            # Сбрасываем состояние и возвращаем к выбору даты
            state_manager.set_admin_state(AdminState.BROADCAST_SCHEDULE_AWAITING_DATE)
            keyboard = create_date_quick_select_keyboard()
            await message.reply_text("Выберите дату для отправки рассылки:", reply_markup=keyboard)
            return
    except ValueError:
        await message.reply_text("Ошибка при обработке даты и времени.")
        state_manager.reset_admin_state()
        return

    # Сохраняем дату и время
    context.user_data["scheduled_broadcast_datetime"] = scheduled_datetime.isoformat()

    # Проверяем текущее состояние, чтобы определить, создаем мы новую рассылку или редактируем существующую
    current_state = state_manager.get_admin_state()
    if current_state == AdminState.BROADCAST_EDIT_AWAITING_TIME:
        # Это изменение времени существующей рассылки
        # В этом случае мы уже обновили дату и время в другом месте,
        # а здесь нужно завершить процесс редактирования
        new_broadcast_date = context.user_data.get("new_broadcast_date")
        if new_broadcast_date:
            # Объединяем выбранную дату и введенное время
            selected_datetime_str = f"{new_broadcast_date} {time_input}"
            new_datetime = dt.strptime(selected_datetime_str, "%Y-%m-%d %H:%M")
            current_datetime = dt.now()
            if new_datetime <= current_datetime:
                await message.reply_text("❌ Ошибка: нельзя запланировать рассылку на прошедшее время. Пожалуйста, выберите будущую дату и время.")
                # Сбрасываем состояние и возвращаем к выбору даты
                state_manager.set_admin_state(AdminState.BROADCAST_EDIT_AWAITING_DATE)
                from handlers.calendar import create_date_quick_select_keyboard
                keyboard = create_date_quick_select_keyboard()
                await message.reply_text("📅 Выберите дату для отправки рассылки:", reply_markup=keyboard)
                return
            
            # Получаем ID рассылки
            broadcast_id = context.user_data.get("broadcast_edit_id")
            if not broadcast_id:
                await message.reply_text("❌ Ошибка: неизвестная рассылка для редактирования.")
                state_manager.reset_admin_state()
                return
            
            # Обновляем дату и время рассылки
            from db_session import get_db
            from models.crud import get_scheduled_broadcast, update_scheduled_broadcast
            with get_db() as db:
                success = update_scheduled_broadcast(
                    db,
                    broadcast_id,
                    scheduled_datetime=new_datetime
                )
            
            if success:
                # Форматируем дату в русском формате
                day = new_datetime.day
                months_map = {
                    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
                    5: "мая", 6: "июня", 7: "июля", 8: "августа",
                    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
                }
                month_name = months_map.get(new_datetime.month, new_datetime.month)
                formatted_date = f"{day} {month_name} {new_datetime.year}"
                
                await message.reply_text(f"✅ Дата и время рассылки успешно обновлены на {formatted_date} в {new_datetime.strftime('%H:%M')}!")
            else:
                await message.reply_text("❌ Не удалось обновить дату и время рассылки.")
            
            # Сбрасываем состояние
            state_manager.reset_admin_state()
            # Очищаем данные
            context.user_data.pop("broadcast_edit_id", None)
            context.user_data.pop("new_broadcast_date", None)
            
            # Добавляем кнопки для возврата
            keyboard = [
                [InlineKeyboardButton("📋 К списку рассылок", callback_data="scheduled_broadcasts_list")]
            ]
            await context.bot.send_message(
                chat_id=message.from_user.id,
                text="Выберите действие:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await message.reply_text("❌ Ошибка: дата не выбрана.")
            state_manager.reset_admin_state()
    else:
        # Это создание новой рассылки
        # Показываем подтверждение
        state_manager.set_admin_state(AdminState.BROADCAST_SCHEDULE_CONFIRMATION)
        
        # Получаем день недели и форматируем дату по-русски
        weekday = scheduled_datetime.strftime('%A')
        weekdays_map = {
            'Monday': 'понедельник',
            'Tuesday': 'вторник',
            'Wednesday': 'среду',
            'Thursday': 'четверг',
            'Friday': 'пятницу',
            'Saturday': 'субботу',
            'Sunday': 'воскресенье'
        }
        weekday_ru = weekdays_map.get(weekday, weekday)
        
        # Форматируем дату в русском формате
        day = scheduled_datetime.day
        months_map = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа",
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }
        month_name = months_map.get(scheduled_datetime.month, scheduled_datetime.month)
        formatted_date = f"{day} {month_name} {scheduled_datetime.year}"
        
        confirmation_text = f"Вы выбрали дату: {formatted_date} в {time_input}\n\nВсе верно?"
        keyboard = [
            [InlineKeyboardButton("✅ Да, все верно", callback_data="scheduled_broadcast_confirm")],
            [InlineKeyboardButton("📅 Изменить дату", callback_data="scheduled_broadcast_change_date")]
        ]
        await message.reply_text(confirmation_text, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_scheduled_broadcast_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка подтверждения отложенной рассылки."""
    query = update.callback_query
    if query is None:
        logger.error("handle_scheduled_broadcast_confirmation: query is None")
        return

    command = query.data
    logger.info(f"handle_scheduled_broadcast_confirmation: получена команда {command}")

    # Проверяем, что пользователь находится в состоянии подтверждения
    state_manager = StateManager(context)
    current_state = state_manager.get_admin_state()
    logger.info(f"handle_scheduled_broadcast_confirmation: текущее состояние {current_state}, ожидалось {AdminState.BROADCAST_SCHEDULE_CONFIRMATION}")
    
    if current_state != AdminState.BROADCAST_SCHEDULE_CONFIRMATION:
        logger.warning(f"Получена команда {command} в состоянии {current_state}, ожидалось BROADCAST_SCHEDULE_CONFIRMATION")
        try:
            await query.edit_message_text("Ошибка: некорректное состояние для подтверждения рассылки.")
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
        return

    logger.info(f"handle_scheduled_broadcast_confirmation: обработка команды {command}")
    
    if command == "scheduled_broadcast_confirm":
        logger.info("handle_scheduled_broadcast_confirmation: обработка подтверждения рассылки")
        # Создаем отложенную рассылку в базе данных
        scheduled_datetime_str = context.user_data.get("scheduled_broadcast_datetime")
        message_id = context.user_data.get("scheduled_broadcast_message_id")
        admin_id = update.effective_user.id

        logger.info(f"handle_scheduled_broadcast_confirmation: данные для рассылки - datetime: {scheduled_datetime_str}, message_id: {message_id}, admin_id: {admin_id}")

        if not all([scheduled_datetime_str, message_id, admin_id]):
            logger.warning(f"Недостаточно данных для создания рассылки: scheduled_datetime_str={bool(scheduled_datetime_str)}, message_id={bool(message_id)}, admin_id={bool(admin_id)}")
            try:
                await query.edit_message_text("Ошибка: необходимые данные для создания рассылки отсутствуют.")
            except Exception as e:
                logger.error(f"Ошибка при редактировании сообщения: {e}")
            state_manager.reset_admin_state()
            return

        from datetime import datetime as dt
        try:
            scheduled_datetime = dt.fromisoformat(scheduled_datetime_str)
            logger.info(f"handle_scheduled_broadcast_confirmation: дата рассылки преобразована: {scheduled_datetime}")
        except ValueError as e:
            logger.error(f"Ошибка преобразования даты: {e}")
            try:
                await query.edit_message_text("Ошибка при обработке даты и времени.")
            except Exception as edit_error:
                logger.error(f"Ошибка при редактировании сообщения: {edit_error}")
            state_manager.reset_admin_state()
            return

        # Подготовим содержимое сообщения в JSON-формате
        # Используем сохраненный оригинальный текст, если он есть
        saved_original_text = context.user_data.get("scheduled_broadcast_original_text")
        saved_photo_id = context.user_data.get("broadcast_photo_id")
        saved_video_id = context.user_data.get("broadcast_video_id")
        saved_document_id = context.user_data.get("broadcast_document_id")
        saved_audio_id = context.user_data.get("broadcast_audio_id")
        saved_voice_id = context.user_data.get("broadcast_voice_id")
        saved_caption = context.user_data.get("broadcast_caption", "")
        
        message_content_dict = {
            "message_id": message_id,
            "chat_id": settings.ADMIN_CHAT_ID
        }
        
        # Добавляем текст, если он есть
        if saved_original_text:
            message_content_dict["original_text"] = saved_original_text
        else:
            # Попробуем получить текст оригинального сообщения для сохранения
            try:
                # Получаем оригинальное сообщение для извлечения текста
                original_message = await context.bot.get_message(
                    chat_id=settings.ADMIN_CHAT_ID,
                    message_id=message_id
                )
                
                # Проверяем, есть ли текст в сообщении
                original_text = getattr(original_message, 'text', None) or getattr(original_message, 'caption', None)
                if original_text:
                    message_content_dict["original_text"] = original_text
            except Exception as e:
                # Если не удалось получить текст, просто продолжаем без него
                logger.warning(f"Не удалось получить текст оригинального сообщения {message_id}: {e}")
        
        # Добавляем медиа-данные, если они есть
        if saved_photo_id:
            message_content_dict["photo_id"] = saved_photo_id
            message_content_dict["caption"] = saved_caption
        elif saved_video_id:
            message_content_dict["video_id"] = saved_video_id
            message_content_dict["caption"] = saved_caption
        elif saved_document_id:
            message_content_dict["document_id"] = saved_document_id
            message_content_dict["caption"] = saved_caption
        elif saved_audio_id:
            message_content_dict["audio_id"] = saved_audio_id
            message_content_dict["caption"] = saved_caption
        elif saved_voice_id:
            message_content_dict["voice_id"] = saved_voice_id
            # Для голосовых сообщений caption не используется в Telegram, сохраняем отдельно для отображения
            message_content_dict["caption"] = saved_caption

        message_content = json.dumps(message_content_dict)

        from db_session import get_db
        try:
            logger.info("handle_scheduled_broadcast_confirmation: сохранение отложенной рассылки в базу данных")
            with get_db() as db:
                scheduled_broadcast = create_scheduled_broadcast(
                    db=db,
                    admin_id=admin_id,
                    message_content=message_content,
                    scheduled_datetime=scheduled_datetime
                )
            logger.info("handle_scheduled_broadcast_confirmation: отложенная рассылка успешно сохранена")
        except Exception as e:
            logger.error(f"Ошибка при создании отложенной рассылки: {e}", exc_info=True)
            try:
                await query.edit_message_text("Ошибка при сохранении отложенной рассылки.")
            except Exception as edit_error:
                logger.error(f"Ошибка при редактировании сообщения: {edit_error}")
            state_manager.reset_admin_state()
            return

        # Очищаем данные
        context.user_data.pop("scheduled_broadcast_datetime", None)
        context.user_data.pop("scheduled_broadcast_message_id", None)
        context.user_data.pop("scheduled_broadcast_date", None)
        context.user_data.pop("scheduled_broadcast_time", None)
        logger.info("handle_scheduled_broadcast_confirmation: данные очищены из user_data")

        state_manager.reset_admin_state()
        logger.info("handle_scheduled_broadcast_confirmation: состояние сброшено")

        # Формируем сообщение с днем недели
        weekday = scheduled_datetime.strftime('%A')
        weekdays_map = {
            'Monday': 'понедельник',
            'Tuesday': 'вторник',
            'Wednesday': 'среду',
            'Thursday': 'четверг',
            'Friday': 'пятницу',
            'Saturday': 'субботу',
            'Sunday': 'воскресенье'
        }
        weekday_ru = weekdays_map.get(weekday, weekday)

        # Форматируем дату в русском формате
        day = scheduled_datetime.day
        months_map = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа",
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }
        month_name = months_map.get(scheduled_datetime.month, scheduled_datetime.month)
        formatted_date = f"{day} {month_name} {scheduled_datetime.year}"
        
        try:
            await query.edit_message_text(f"Рассылка запланирована на {weekday_ru} {formatted_date} в {scheduled_datetime.strftime('%H:%M')}")
            logger.info("handle_scheduled_broadcast_confirmation: сообщение о планировании рассылки отправлено")
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения с подтверждением: {e}")

        # Добавляем кнопки для управления
        keyboard = [
            [InlineKeyboardButton("📋 Все запланированные рассылки", callback_data="scheduled_broadcasts_list")],
            [InlineKeyboardButton("➕ Новая рассылка", callback_data="admin_broadcast")]
        ]
        try:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text="Выберите действие:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            logger.info("handle_scheduled_broadcast_confirmation: сообщение с кнопками управления отправлено")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения с кнопками управления: {e}")

    elif command == "scheduled_broadcast_change_date":
        logger.info("handle_scheduled_broadcast_confirmation: обработка изменения даты")
        # Возвращаемся к выбору даты
        state_manager.set_admin_state(AdminState.BROADCAST_SCHEDULE_AWAITING_DATE)
        logger.info("handle_scheduled_broadcast_confirmation: установлено состояние BROADCAST_SCHEDULE_AWAITING_DATE")
        
        # Показываем календарь для выбора новой даты
        current_date = datetime.now(ZoneInfo("Europe/Minsk")).date()
        calendar_keyboard = create_calendar_keyboard(current_date)
        try:
            await query.edit_message_text("Выберите новую дату для отправки рассылки:", reply_markup=calendar_keyboard)
            logger.info("handle_scheduled_broadcast_confirmation: календарь для выбора новой даты отправлен")
        except Exception as e:
            logger.error(f"Ошибка при отправке календаря для изменения даты: {e}")
            try:
                await query.edit_message_text("Произошла ошибка при открытии календаря.")
            except:
                pass
    else:
        logger.warning(f"handle_scheduled_broadcast_confirmation: неизвестная команда {command}")


async def handle_scheduled_broadcasts_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка запроса на отображение списка запланированных рассылок."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    
    admin_id = update.effective_user.id

    from db_session import get_db
    with get_db() as db:
        scheduled_broadcasts = get_scheduled_broadcasts_by_admin(db, admin_id)
    
    if not scheduled_broadcasts:
        await query.edit_message_text("У вас нет запланированных рассылок.")
        keyboard = [
            [InlineKeyboardButton("➕ Создать новую рассылку", callback_data="admin_broadcast")],
            [InlineKeyboardButton("⬅️ Назад в админку", callback_data="admin_main")]
        ]
        # Используем chat_id из callback_query, так как query.message может быть None после edit
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Формируем список рассылок
    keyboard = []
    for broadcast in scheduled_broadcasts:
        # Получаем дату и превью сообщения
        broadcast_date = broadcast.scheduled_datetime.strftime('%d.%m.%Y %H:%M')
        message_content = json.loads(broadcast.message_content)
        new_text = message_content.get("new_text")
        
        if new_text:
            # Если есть обновленный текст, показываем первые 50 символов с многоточием при необходимости
            preview_text = new_text[:50] + "..." if len(new_text) > 50 else new_text
        else:
            # Проверяем, есть ли оригинальный текст сообщения
            original_text = message_content.get("original_text")
            if original_text:
                preview_text = original_text[:50] + "..." if len(original_text) > 50 else original_text
            else:
                preview_text = "Текст не найден"
        
        button_text = f"{broadcast_date} - {preview_text}"
        callback_data = f"scheduled_broadcast_view_{broadcast.id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Добавляем кнопку назад
    keyboard.append([InlineKeyboardButton("⬅️ Назад в админку", callback_data="admin_main")])
    
    try:
        await query.edit_message_text("Ваши запланированные рассылки:", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception:
        # Если не удалось отредактировать сообщение (например, оно устарело), отправляем новое
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="Ваши запланированные рассылки:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def handle_scheduled_broadcast_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка запроса на просмотр конкретной запланированной рассылки."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    
    # Извлекаем ID рассылки из callback_data
    command = query.data
    broadcast_id = int(command.split("_")[-1])
    
    admin_id = update.effective_user.id
    from db_session import get_db
    from models.crud import get_scheduled_broadcast
    with get_db() as db:
        broadcast = get_scheduled_broadcast(db, broadcast_id)
        
        if not broadcast or broadcast.admin_id != admin_id:
            await query.edit_message_text("❌ Рассылка не найдена или недоступна.")
            return
    
    # Получаем текст рассылки для отображения
    message_content = json.loads(broadcast.message_content)
    new_text = message_content.get("new_text")
    original_text = message_content.get("original_text")
    message_id = message_content.get("message_id", "Неизвестно")
    
    # Проверяем наличие медиа-контента в сообщении
    photo_id = message_content.get("photo_id")
    video_id = message_content.get("video_id")
    document_id = message_content.get("document_id")
    audio_id = message_content.get("audio_id")
    voice_id = message_content.get("voice_id")
    caption = message_content.get("caption", "")
    
    # Если есть медиа-контент, отправляем его с соответствующим методом
    if photo_id:
        # Отправляем фото с подписью
        full_caption = new_text or original_text or caption or f"ID сообщения: {message_id}"
        # Ограничиваем длину подписи до 1024 символов (максимум для Telegram)
        if len(full_caption) > 1024:
            full_caption = full_caption[:1021] + "..."
        await context.bot.send_photo(
            chat_id=query.from_user.id,
            photo=photo_id,
            caption=full_caption
        )
    elif video_id:
        # Отправляем видео с подписью
        full_caption = new_text or original_text or caption or f"ID сообщения: {message_id}"
        # Ограничиваем длину подписи до 1024 символов (максимум для Telegram)
        if len(full_caption) > 1024:
            full_caption = full_caption[:1021] + "..."
        await context.bot.send_video(
            chat_id=query.from_user.id,
            video=video_id,
            caption=full_caption
        )
    elif document_id:
        # Отправляем документ с подписью
        full_caption = new_text or original_text or caption or f"ID сообщения: {message_id}"
        # Ограничиваем длину подписи до 1024 символов (максимум для Telegram)
        if len(full_caption) > 1024:
            full_caption = full_caption[:1021] + "..."
        await context.bot.send_document(
            chat_id=query.from_user.id,
            document=document_id,
            caption=full_caption
        )
    elif audio_id:
        # Отправляем аудио с подписью
        full_caption = new_text or original_text or caption or f"ID сообщения: {message_id}"
        # Ограничиваем длину подписи до 1024 символов (максимум для Telegram)
        if len(full_caption) > 1024:
            full_caption = full_caption[:1021] + "..."
        await context.bot.send_audio(
            chat_id=query.from_user.id,
            audio=audio_id,
            caption=full_caption
        )
    elif voice_id:
        # Отправляем голосовое сообщение
        # Для голосовых сообщений подпись не нужна, но добавим текст для идентификации
        voice_caption = new_text or original_text or caption or f"ID сообщения: {message_id}"
        # Ограничиваем длину подписи до 1024 символов (максимум для Telegram)
        if len(voice_caption) > 1024:
            voice_caption = voice_caption[:1021] + "..."
        # Отправляем голосовое сообщение без caption, так как Telegram не поддерживает caption для голосовых сообщений
        await context.bot.send_voice(
            chat_id=query.from_user.id,
            voice=voice_id
        )
        # Отправляем текст отдельным сообщением, только если это не стандартное сообщение об ID
        if voice_caption != f"ID сообщения: {message_id}":
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=voice_caption
            )
    else:
        # Отправляем обычное текстовое сообщение
        if new_text:
            full_post_text = new_text
        elif original_text:
            full_post_text = original_text
        elif caption:
            full_post_text = caption
        else:
            full_post_text = f"Текст не найден. ID сообщения: {message_id}"
        
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=full_post_text
        )
    
    # Отправляем второе сообщение с датой и временем рассылки
    broadcast_date = broadcast.scheduled_datetime.strftime('%d.%m.%Y %H:%M')
    time_info_text = f"📅 Дата и время рассылки: {broadcast_date}"
    
    # Кнопки для управления рассылкой
    keyboard = [
        [InlineKeyboardButton("✏️ Изменить текст", callback_data=f"scheduled_broadcast_edit_text_{broadcast.id}")],
        [InlineKeyboardButton("📅 Изменить дату и время", callback_data=f"scheduled_broadcast_edit_datetime_{broadcast.id}")],
        [InlineKeyboardButton("🗑️ Удалить рассылку", callback_data=f"scheduled_broadcast_delete_{broadcast.id}")],
        [InlineKeyboardButton("⬅️ Назад к списку", callback_data="scheduled_broadcasts_list")]
    ]
    
    await query.edit_message_text(time_info_text, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_broadcast_edit_text_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запрашивает у пользователя новый текст для рассылки."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    
    # Извлекаем ID рассылки из callback_data
    command = query.data
    broadcast_id = int(command.split("_")[-1])
    
    # Сохраняем ID рассылки в контексте для дальнейшего использования
    context.user_data["broadcast_edit_id"] = broadcast_id
    
    # Устанавливаем состояние ожидания нового текста
    from services.state_manager import StateManager
    state_manager = StateManager(context)
    state_manager.set_admin_state(AdminState.BROADCAST_EDIT_AWAITING_TEXT)
    
    await query.edit_message_text("✏️ Отправьте новый текст для рассылки:")
    
    # Добавляем кнопку отмены
    keyboard = [
        [InlineKeyboardButton("❌ Отмена", callback_data="scheduled_broadcast_cancel_edit")]
    ]
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text="Нажмите кнопку ниже для отмены редактирования:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_broadcast_edit_datetime_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начинает процесс изменения даты и времени рассылки."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    
    # Извлекаем ID рассылки из callback_data
    command = query.data
    broadcast_id = int(command.split("_")[-1])
    
    # Сохраняем ID рассылки в контексте для дальнейшего использования
    context.user_data["broadcast_edit_id"] = broadcast_id
    
    # Устанавливаем состояние ожидания выбора новой даты
    from services.state_manager import StateManager
    state_manager = StateManager(context)
    state_manager.set_admin_state(AdminState.BROADCAST_EDIT_AWAITING_DATE)
    
    # Показываем кнопки выбора даты
    from handlers.calendar import create_date_quick_select_keyboard
    keyboard = create_date_quick_select_keyboard()
    await query.edit_message_text("📅 Выберите новую дату для рассылки:", reply_markup=keyboard)


async def handle_broadcast_delete_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запрашивает подтверждение на удаление рассылки."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    
    # Извлекаем ID рассылки из callback_data
    command = query.data
    broadcast_id = int(command.split("_")[-1])
    
    # Сохраняем ID рассылки в контексте для дальнейшего использования
    context.user_data["broadcast_delete_id"] = broadcast_id
    
    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data=f"scheduled_broadcast_delete_confirm_{broadcast_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data="scheduled_broadcasts_list")]
    ]
    
    await query.edit_message_text("⚠️ Вы уверены, что хотите удалить эту рассылку?", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_broadcast_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Подтверждает и выполняет удаление рассылки."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    
    # Извлекаем ID рассылки из callback_data
    command = query.data
    broadcast_id = int(command.split("_")[-1])
    
    from db_session import get_db
    with get_db() as db:
        from models.crud import delete_scheduled_broadcast
        success = delete_scheduled_broadcast(db, broadcast_id)
    
    if success:
        await query.edit_message_text("✅ Рассылка успешно удалена!")
    else:
        await query.edit_message_text("❌ Не удалось удалить рассылку. Возможно, она уже была удалена.")
    
    # Добавляем кнопку для возврата к списку
    keyboard = [
        [InlineKeyboardButton("📋 К списку рассылок", callback_data="scheduled_broadcasts_list")]
    ]
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text="Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_broadcast_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает новый текст для рассылки."""
    message = update.message
    if message is None:
        return

    # Проверяем, что мы в нужном состоянии
    from services.state_manager import StateManager
    state_manager = StateManager(context)
    current_state = state_manager.get_admin_state()
    
    if current_state != AdminState.BROADCAST_EDIT_AWAITING_TEXT:
        return
    
    # Получаем ID рассылки
    broadcast_id = context.user_data.get("broadcast_edit_id")
    if not broadcast_id:
        await message.reply_text("❌ Ошибка: неизвестная рассылка для редактирования.")
        state_manager.reset_admin_state()
        return
    
    # Получаем новый текст (в данном случае - это новое содержимое сообщения)
    new_text = message.text or message.caption
    
    if not new_text:
        # Проверяем, может быть, это медиа-сообщение с описанием
        if hasattr(message, 'caption') and message.caption:
            new_text = message.caption
        else:
            await message.reply_text("❌ Пожалуйста, отправьте текст для новой рассылки.")
            return
    
    # Обновляем содержимое рассылки
    from db_session import get_db
    from models.crud import get_scheduled_broadcast, update_scheduled_broadcast
    with get_db() as db:
        existing_broadcast = get_scheduled_broadcast(db, broadcast_id)
        if not existing_broadcast:
            await message.reply_text("❌ Рассылка не найдена.")
            state_manager.reset_admin_state()
            return
        
        # Обновляем содержимое сообщения в JSON
        import json
        message_content = json.loads(existing_broadcast.message_content)
        # Обновляем или добавляем новый текст
        message_content["new_text"] = new_text  # Добавляем новый текст к существующему содержимому
        
        success = update_scheduled_broadcast(
            db,
            broadcast_id,
            message_content=json.dumps(message_content)
        )
    
    if success:
        await message.reply_text("✅ Текст рассылки успешно обновлен!")
    else:
        await message.reply_text("❌ Не удалось обновить текст рассылки.")
    
    # Сбрасываем состояние
    state_manager.reset_admin_state()
    # Очищаем данные
    context.user_data.pop("broadcast_edit_id", None)
    
    # Добавляем кнопки для возврата
    keyboard = [
        [InlineKeyboardButton("📋 К списку рассылок", callback_data="scheduled_broadcasts_list")]
    ]
    await context.bot.send_message(
        chat_id=message.from_user.id,
        text="Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_broadcast_edit_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ввод нового времени для рассылки."""
    message = update.message
    if message is None:
        return

    # Проверяем, что мы в нужном состоянии
    from services.state_manager import StateManager
    state_manager = StateManager(context)
    current_state = state_manager.get_admin_state()
    
    if current_state != AdminState.BROADCAST_EDIT_AWAITING_TIME:
        return
    
    time_input = message.text.strip()

    # Проверяем формат времени (ЧЧ:М)
    import re
    time_pattern = r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
    if not re.match(time_pattern, time_input):
        await message.reply_text("❌ Неверный формат времени. Пожалуйста, введите время в формате ЧЧ:ММ (например, 14:30)")
        return

    # Добавляем 0 в начало, если нужно
    if len(time_input.split(':')[0]) == 1:
        time_input = '0' + time_input

    # Сохраняем новое время
    context.user_data["new_broadcast_time"] = time_input
    
    # Получаем дату и время
    selected_date_str = context.user_data.get("new_broadcast_date")
    selected_time_str = context.user_data.get("new_broadcast_time")
    
    if not selected_date_str or not selected_time_str:
        await message.reply_text("❌ Ошибка: дата или время не выбраны.")
        state_manager.reset_admin_state()
        return

    from datetime import datetime as dt
    try:
        # Объединяем выбранную дату и время
        selected_datetime_str = f"{selected_date_str} {selected_time_str}"
        new_datetime = dt.strptime(selected_datetime_str, "%Y-%m-%d %H:%M")
        current_datetime = dt.now()
        if new_datetime <= current_datetime:
            await message.reply_text("❌ Ошибка: нельзя запланировать рассылку на прошедшее время. Пожалуйста, выберите будущую дату и время.")
            # Сбрасываем состояние и возвращаем к выбору даты
            state_manager.set_admin_state(AdminState.BROADCAST_EDIT_AWAITING_DATE)
            from handlers.calendar import create_date_quick_select_keyboard
            keyboard = create_date_quick_select_keyboard()
            await message.reply_text("📅 Выберите дату для отправки рассылки:", reply_markup=keyboard)
            return
    except ValueError:
        await message.reply_text("❌ Ошибка при обработке даты и времени.")
        state_manager.reset_admin_state()
        return

    # Получаем ID рассылки
    broadcast_id = context.user_data.get("broadcast_edit_id")
    if not broadcast_id:
        await message.reply_text("❌ Ошибка: неизвестная рассылка для редактирования.")
        state_manager.reset_admin_state()
        return
    
    # Обновляем дату и время рассылки
    from db_session import get_db
    from models.crud import update_scheduled_broadcast
    with get_db() as db:
        success = update_scheduled_broadcast(
            db,
            broadcast_id,
            scheduled_datetime=new_datetime
        )
    
    if success:
        # Форматируем дату в русском формате
        day = new_datetime.day
        months_map = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа",
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }
        month_name = months_map.get(new_datetime.month, new_datetime.month)
        formatted_date = f"{day} {month_name} {new_datetime.year}"
        
        await message.reply_text(f"✅ Дата и время рассылки успешно обновлены на {formatted_date} в {new_datetime.strftime('%H:%M')}!")
    else:
        await message.reply_text("❌ Не удалось обновить дату и время рассылки.")
    
    # Сбрасываем состояние
    state_manager.reset_admin_state()
    # Очищаем данные
    context.user_data.pop("broadcast_edit_id", None)
    context.user_data.pop("new_broadcast_date", None)
    context.user_data.pop("new_broadcast_time", None)
    
    # Добавляем кнопки для возврата
    keyboard = [
        [InlineKeyboardButton("📋 К списку рассылок", callback_data="scheduled_broadcasts_list")]
    ]
    await message.reply_text("Выберите действие:", reply_markup=InlineKeyboardMarkup(keyboard))
