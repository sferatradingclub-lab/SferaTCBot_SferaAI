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
from models.crud import iter_broadcast_targets, create_scheduled_broadcast, get_scheduled_broadcasts_by_admin
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
            from datetime import datetime
            selected_date_obj = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
            day = selected_date_obj.day
            months_map = {
                1: "января", 2: "февраля", 3: "марта", 4: "апреля",
                5: "мая", 6: "июня", 7: "июля", 8: "августа",
                9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
            }
            month_name = months_map.get(selected_date_obj.month, selected_date_obj.month)
            formatted_date = f"{day} {month_name} {selected_date_obj.year}"

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
                from datetime import date
                target_date = date(year, month, 1)
                new_keyboard = create_calendar_keyboard(target_date)
                await query.edit_message_reply_markup(reply_markup=new_keyboard)
            except ValueError:
                await query.edit_message_text("Ошибка при обработке даты.")

        elif command == "calendar_expand":
            logger.info("Обработка команды calendar_expand")
            # Развернуть полный календарь
            from datetime import date
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
                    from datetime import date
                    current_date = date.today()
                    calendar_keyboard = create_calendar_keyboard(current_date)
                    await query.message.reply_text("Выберите дату:", reply_markup=calendar_keyboard)
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

    from datetime import datetime
    try:
        # Объединяем выбранную дату и время
        selected_datetime_str = f"{selected_date_str} {selected_time_str}"
        scheduled_datetime = datetime.strptime(selected_datetime_str, "%Y-%m-%d %H:%M")
        current_datetime = datetime.now()
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
        return

    await query.answer()
    command = query.data

    # Проверяем, что пользователь находится в состоянии подтверждения
    state_manager = StateManager(context)
    current_state = state_manager.get_admin_state()
    
    # Вместо возврата с ошибкой, просто логируем неожиданное состояние и продолжаем
    if current_state != AdminState.BROADCAST_SCHEDULE_CONFIRMATION:
        logger.warning(f"Получена команда {command} в состоянии {current_state}, ожидалось BROADCAST_SCHEDULE_CONFIRMATION")

    if command == "scheduled_broadcast_confirm":
        # Создаем отложенную рассылку в базе данных
        scheduled_datetime_str = context.user_data.get("scheduled_broadcast_datetime")
        message_id = context.user_data.get("scheduled_broadcast_message_id")
        admin_id = update.effective_user.id

        if not all([scheduled_datetime_str, message_id, admin_id]):
            await query.edit_message_text("Ошибка при создании отложенной рассылки.")
            state_manager.reset_admin_state()
            return

        from datetime import datetime
        try:
            scheduled_datetime = datetime.fromisoformat(scheduled_datetime_str)
        except ValueError:
            await query.edit_message_text("Ошибка при обработке даты и времени.")
            state_manager.reset_admin_state()
            return

        # Подготовим содержимое сообщения в JSON-формате
        # Для простоты в этом примере будем сохранять только ID сообщения
        # В реальной реализации нужно будет сериализовать все содержимое сообщения
        message_content = json.dumps({
            "message_id": message_id,
            "chat_id": settings.ADMIN_CHAT_ID
        })

        from db_session import get_db
        try:
            with get_db() as db:
                scheduled_broadcast = create_scheduled_broadcast(
                    db=db,
                    admin_id=admin_id,
                    message_content=message_content,
                    scheduled_datetime=scheduled_datetime
                )
        except Exception as e:
            logger.error(f"Ошибка при создании отложенной рассылки: {e}", exc_info=True)
            await query.edit_message_text("Ошибка при сохранении отложенной рассылки.")
            state_manager.reset_admin_state()
            return

        # Очищаем данные
        context.user_data.pop("scheduled_broadcast_datetime", None)
        context.user_data.pop("scheduled_broadcast_message_id", None)
        context.user_data.pop("scheduled_broadcast_date", None)
        context.user_data.pop("scheduled_broadcast_time", None)

        state_manager.reset_admin_state()

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
        
        await query.edit_message_text(f"Рассылка запланирована на {weekday_ru} {formatted_date} в {scheduled_datetime.strftime('%H:%M')}")

        # Добавляем кнопки для управления
        keyboard = [
            [InlineKeyboardButton("📋 Все запланированные рассылки", callback_data="scheduled_broadcasts_list")],
            [InlineKeyboardButton("➕ Новая рассылка", callback_data="admin_broadcast")]
        ]
        await query.message.reply_text("Выберите действие:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif command == "scheduled_broadcast_change_date":
        # Возвращаемся к выбору даты
        state_manager.set_admin_state(AdminState.BROADCAST_SCHEDULE_AWAITING_DATE)
        
        # Показываем календарь для выбора новой даты
        from datetime import date
        current_date = datetime.now(ZoneInfo("Europe/Minsk")).date()
        calendar_keyboard = create_calendar_keyboard(current_date)
        await query.edit_message_text("Выберите новую дату для отправки рассылки:", reply_markup=calendar_keyboard)


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
        await query.message.reply_text("Выберите действие:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Формируем список рассылок
    keyboard = []
    for broadcast in scheduled_broadcasts:
        # Получаем дату и первые 30 символов сообщения
        broadcast_date = broadcast.scheduled_datetime.strftime('%d.%m.%Y %H:%M')
        message_preview = json.loads(broadcast.message_content).get("message_id", "Сообщение")
        # Ограничиваем длину превью
        preview_text = str(message_preview)[:30] + "..." if len(str(message_preview)) > 30 else str(message_preview)
        button_text = f"{broadcast_date} - {preview_text}"
        callback_data = f"scheduled_broadcast_view_{broadcast.id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Добавляем кнопку назад
    keyboard.append([InlineKeyboardButton("⬅️ Назад в админку", callback_data="admin_main")])
    
    await query.edit_message_text("Ваши запланированные рассылки:", reply_markup=InlineKeyboardMarkup(keyboard))
