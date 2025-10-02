from telegram import Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from config import logger, TOOLS_DATA, TOOLS_IMAGE_ID
from keyboards import get_tools_categories_keyboard

async def show_tools_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет начальное меню раздела 'Полезные инструменты'."""
    await update.message.reply_photo(
        photo=TOOLS_IMAGE_ID, 
        caption="Здесь мы собрали полезные инструменты для трейдера. Выберите нужный раздел:", 
        reply_markup=get_tools_categories_keyboard()
    )

async def tools_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает все нажатия на инлайн-кнопки в разделе 'Полезные инструменты'."""
    query = update.callback_query
    await query.answer()
    query_data = query.data
    
    if query_data == 'tools_main':
        keyboard = get_tools_categories_keyboard()
        media = InputMediaPhoto(media=TOOLS_IMAGE_ID, caption="Здесь мы собрали полезные инструменты для трейдера. Выберите нужный раздел:")
        try:
            await query.edit_message_media(media=media, reply_markup=keyboard)
        except TelegramError as e:
            if "Message is not modified" not in e.message: 
                logger.warning(f"Error in tools_main: {e}")
        return

    if query_data.startswith('tools_'):
        category_key = query_data.split('_', 1)[1]
        category = TOOLS_DATA.get(category_key)
        
        if not category or not category.get('items'):
            text = "Этот раздел пока пуст, но скоро мы его наполним!"
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад к разделам", callback_data='tools_main')]])
        else:
            text = category.get('intro_text', 'Выберите инструмент:')
            buttons = [[InlineKeyboardButton(item['name'], callback_data=item['callback'])] for item in category['items']]
            buttons.append([InlineKeyboardButton("⬅️ Назад к разделам", callback_data='tools_main')])
            keyboard = InlineKeyboardMarkup(buttons)

        await query.edit_message_caption(caption=text, reply_markup=keyboard)
        return

    if query_data.startswith('tool_'):
        selected_tool, parent_category_callback = None, 'tools_main'
        for cat_name, cat_data in TOOLS_DATA.items():
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
            media = InputMediaPhoto(media=selected_tool['image_id'], caption=caption, parse_mode='Markdown')
            try:
                await query.edit_message_media(media=media, reply_markup=InlineKeyboardMarkup(keyboard_buttons))
            except TelegramError as e:
                if "Message is not modified" not in e.message: 
                    logger.warning(f"Error editing tool media: {e}")