from datetime import datetime, date, timedelta
from typing import List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def create_calendar_keyboard(target_date: date = None) -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру с календарем для выбора даты.
    
    Args:
        target_date: Дата, для которой отображается календарь (по умолчанию - текущая дата)
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с календарем
    """
    if target_date is None:
        target_date = date.today()
    
    # Получаем первый день месяца и день недели
    first_day = date(target_date.year, target_date.month, 1)
    start_weekday = first_day.weekday()  # 0 - понедельник, 6 - воскресенье
    
    # Получаем количество дней в месяце
    if target_date.month == 12:
        next_month = date(target_date.year + 1, 1, 1)
    else:
        next_month = date(target_date.year, target_date.month + 1, 1)
    
    last_day_of_month = (next_month - timedelta(days=1)).day  # Вычитаем 1 день от первого дня следующего месяца
    
    # Формируем клавиатуру
    keyboard = []
    
    # Заголовок с навигацией по месяцам
    prev_month = target_date.month - 1 if target_date.month > 1 else 12
    prev_year = target_date.year if target_date.month > 1 else target_date.year - 1
    
    next_month = target_date.month + 1 if target_date.month < 12 else 1
    next_year = target_date.year if target_date.month < 12 else target_date.year + 1
    
    header_row = [
        InlineKeyboardButton("<<", callback_data=f"calendar_prev_month_{prev_year}-{prev_month:02d}"),
        InlineKeyboardButton(f"{target_date.strftime('%B %Y')}", callback_data="calendar_noop"),
        InlineKeyboardButton(">>", callback_data=f"calendar_next_month_{next_year}-{next_month:02d}")
    ]
    keyboard.append(header_row)
    
    # Дни недели
    weekdays_row = [
        InlineKeyboardButton("Пн", callback_data="calendar_noop"),
        InlineKeyboardButton("Вт", callback_data="calendar_noop"),
        InlineKeyboardButton("Ср", callback_data="calendar_noop"),
        InlineKeyboardButton("Чт", callback_data="calendar_noop"),
        InlineKeyboardButton("Пт", callback_data="calendar_noop"),
        InlineKeyboardButton("Сб", callback_data="calendar_noop"),
        InlineKeyboardButton("Вс", callback_data="calendar_noop")
    ]
    keyboard.append(weekdays_row)
    
    # Создаем строки календаря
    current_date = date(target_date.year, target_date.month, 1)
    week_row = []
    
    # Добавляем пустые кнопки для дней до начала месяца
    for i in range(start_weekday):
        week_row.append(InlineKeyboardButton(" ", callback_data="calendar_noop"))
    
    # Добавляем дни месяца
    for day in range(1, last_day_of_month + 1):
        current_date = date(target_date.year, target_date.month, day)
        
        # Проверяем, является ли дата прошедшей
        is_past = current_date < date.today()
        
        if is_past:
            # Для прошедших дат используем серую кнопку
            button_text = str(day)
            callback_data = "calendar_noop"
        else:
            # Для будущих дат используем обычную кнопку
            button_text = str(day)
            callback_data = f"calendar_select_{current_date.strftime('%Y-%m-%d')}"
        
        week_row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        
        # Если неделя заполнена или это последний день месяца, добавляем строку
        if len(week_row) == 7 or day == last_day_of_month:
            keyboard.append(week_row)
            week_row = []
    
    # Если последняя строка не пуста, добавляем пустые кнопки до полной недели
    if week_row:
        while len(week_row) < 7:
            week_row.append(InlineKeyboardButton(" ", callback_data="calendar_noop"))
        keyboard.append(week_row)
    
    return InlineKeyboardMarkup(keyboard)


def create_date_quick_select_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с быстрым выбором даты (сегодня, завтра, послезавтра).
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками быстрого выбора
    """
    from datetime import timedelta
    today = date.today()
    tomorrow = today + timedelta(days=1)  # 1 день
    day_after_tomorrow = today + timedelta(days=2)
    
    keyboard = [
        [
            InlineKeyboardButton(f"Сегодня ({today.strftime('%d.%m')})", 
                                callback_data=f"calendar_select_{today.strftime('%Y-%m-%d')}"),
            InlineKeyboardButton(f"Завтра ({tomorrow.strftime('%d.%m')})", 
                                callback_data=f"calendar_select_{tomorrow.strftime('%Y-%m-%d')}")
        ],
        [
            InlineKeyboardButton(f"Послезавтра ({day_after_tomorrow.strftime('%d.%m')})", 
                                callback_data=f"calendar_select_{day_after_tomorrow.strftime('%Y-%m-%d')}")
        ],
        [
            InlineKeyboardButton("📅 Развернуть календарь", 
                                callback_data="calendar_expand")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)