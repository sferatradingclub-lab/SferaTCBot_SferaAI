from telegram import Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from config import get_safe_url, get_settings, send_video_or_photo_fallback, get_video_or_photo_urls
from keyboards import get_tools_categories_keyboard

settings = get_settings()
logger = settings.logger

from .error_handler import handle_errors

TOOLS_MENU_TEXT = "Здесь мы собрали полезные инструменты для трейдера. Выберите нужный раздел:"


@handle_errors
async def show_tools_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет начальное меню раздела 'Полезные инструменты'."""
    if not update.message:
        return

    # Используем отдельные переменные для видео и изображения
    tools_video_url, tools_photo_url = get_video_or_photo_urls(settings, "TOOLS")
    keyboard = get_tools_categories_keyboard()

    await send_video_or_photo_fallback(
        message=update.message,
        video_url=tools_video_url,
        photo_url=tools_photo_url,
        caption=TOOLS_MENU_TEXT,
        reply_markup=keyboard
    )


@handle_errors
async def tools_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает все нажатия на инлайн-кнопки в разделе 'Полезные инструменты'."""
    query = update.callback_query
    await query.answer()
    query_data = query.data

    if query_data == 'tools_main':
        keyboard = get_tools_categories_keyboard()
        # Используем универсальную функцию для обработки inline-редактирования
        # Используем отдельные переменные для видео и изображения
        tools_video_url, tools_photo_url = get_video_or_photo_urls(settings, "TOOLS")
        await send_video_or_photo_fallback(
            query=query,
            video_url=tools_video_url,
            photo_url=tools_photo_url,
            caption=TOOLS_MENU_TEXT,
            reply_markup=keyboard
        )
        return

    if query_data.startswith('tools_'):
        category_key = query_data.split('_', 1)[1]
        category = settings.TOOLS_DATA.get(category_key)

        if not category or not category.get('items'):
            text = "Этот раздел пока пуст, но скоро мы его наполним!"
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад к разделам", callback_data='tools_main')]])
        else:
            text = category.get('intro_text', 'Выберите инструмент:')
            buttons = [[InlineKeyboardButton(item['name'], callback_data=item['callback'])] for item in category['items']]
            buttons.append([InlineKeyboardButton("⬅️ Назад к разделам", callback_data='tools_main')])
            keyboard = InlineKeyboardMarkup(buttons)

        if query.message and (query.message.photo or query.message.animation or query.message.video):
            await query.edit_message_caption(caption=text, reply_markup=keyboard)
        else:
            await query.edit_message_text(text=text, reply_markup=keyboard)
        return

    if query_data.startswith('tool_'):
        selected_tool, parent_category_callback = None, 'tools_main'
        for cat_name, cat_data in settings.TOOLS_DATA.items():
            for item in cat_data['items']:
                if item['callback'] == query_data:
                    selected_tool, parent_category_callback = item, f"tools_{cat_name}"
                    break
            if selected_tool:
                break

        if selected_tool:
            caption = f"*{selected_tool['name']}*\n\n{selected_tool['description']}"
            keyboard_buttons = [
                [
                    InlineKeyboardButton("🔗 Открыть счет", url=selected_tool['site_url']),
                    InlineKeyboardButton("🎬 Посмотреть обзор", url=selected_tool['video_url'])
                ],
                [InlineKeyboardButton("⬅️ Назад к списку", callback_data=parent_category_callback)]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard_buttons)

            # Используем универсальную функцию для обработки inline-редактирования
            # Для отдельных инструментов используем отдельные поля для видео и изображения
            # Не выводим предупреждение, если image_url отсутствует, так как это допустимо
            tool_photo_url = get_safe_url(selected_tool.get('image_url'), selected_tool['name'], warn_if_missing=False)
            # Используем отдельное поле video_url для видео
            tool_video_url = get_safe_url(selected_tool.get('video_url'), selected_tool['name'], warn_if_missing=False)
            # Если есть отдельное видео, используем его, иначе используем фото как fallback
            video_to_use = tool_video_url or tool_photo_url
            # Если есть изображение или видео, показываем медиа
            if tool_photo_url or tool_video_url:
                await send_video_or_photo_fallback(
                    query=query,
                    video_url=video_to_use,
                    photo_url=tool_photo_url,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                # Если нет URL изображения/видео, просто редактируем текст
                try:
                    if query.message and (query.message.photo or query.message.animation or query.message.video):
                        await query.edit_message_caption(
                            caption=caption,
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                    else:
                        await query.edit_message_text(
                            text=caption,
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                except Exception as e:
                    # Если не удалось отредактировать сообщение, отправляем новое
                    settings.logger.warning(f"Не удалось отредактировать сообщение: {e}. Отправляем новое сообщение.")
                    await query.answer("Обновляем информацию...")
                    await query.message.reply_text(
                        text=caption,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
