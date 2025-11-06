import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from telegram import Bot
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from config import get_settings
from db_session import get_db
from models.crud import get_pending_scheduled_broadcasts, mark_broadcast_as_sent, iter_broadcast_targets
from models.user import User
from services.notifier import Notifier

settings = get_settings()


class BroadcastSchedulerService:
    """Служба для планирования и отправки отложенных рассылок."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = settings.logger

    async def process_scheduled_broadcasts(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обрабатывает все запланированные рассылки, которые должны быть отправлены."""
        self.logger.info("Запуск обработки запланированных рассылок")
        
        with get_db() as db:
            scheduled_broadcasts = get_pending_scheduled_broadcasts(db)
        
        if not scheduled_broadcasts:
            self.logger.info("Нет запланированных рассылок для отправки")
            return
        
        self.logger.info(f"Найдено {len(scheduled_broadcasts)} запланированных рассылок для отправки")
        
        for scheduled_broadcast in scheduled_broadcasts:
            try:
                # Десериализуем содержимое сообщения
                message_data = json.loads(scheduled_broadcast.message_content)
                
                # Отправляем рассылку
                await self._send_scheduled_broadcast(scheduled_broadcast, message_data)
                
                # Отмечаем как отправленную
                with get_db() as db:
                    mark_broadcast_as_sent(db, scheduled_broadcast.id)
                
                self.logger.info(f"Рассылка {scheduled_broadcast.id} успешно отправлена и отмечена как отправленная")
                
            except Exception as e:
                self.logger.error(f"Ошибка при отправке запланированной рассылки {scheduled_broadcast.id}: {e}")
    
    async def _send_scheduled_broadcast(self, scheduled_broadcast, message_data: Dict[str, Any]) -> None:
        """Отправляет конкретную запланированную рассылку."""
        from models.crud import iter_broadcast_targets
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        # Проверяем, есть ли обновленный текст у рассылки
        new_text = message_data.get("new_text")
        
        # Проверяем, есть ли кнопки
        buttons_data = message_data.get("buttons")
        reply_markup = None
        if buttons_data and isinstance(buttons_data, list) and len(buttons_data) > 0:
            # Преобразуем кнопки в формат InlineKeyboardMarkup
            try:
                keyboard = []
                for row in buttons_data:
                    if isinstance(row, list):
                        keyboard_row = []
                        for button_text in row:
                            if isinstance(button_text, str):
                                # Для простых кнопок создаем callback_data на основе текста
                                keyboard_row.append(InlineKeyboardButton(button_text, callback_data=f"broadcast_btn_{button_text[:20]}"))
                            elif isinstance(button_text, dict) and "text" in button_text and "callback_data" in button_text:
                                # Для кнопок с явной callback_data
                                keyboard_row.append(InlineKeyboardButton(
                                    button_text["text"],
                                    callback_data=button_text["callback_data"]
                                ))
                        keyboard.append(keyboard_row)
                if keyboard:
                    reply_markup = InlineKeyboardMarkup(keyboard)
            except Exception as e:
                self.logger.warning(f"Ошибка при создании клавиатуры для рассылки: {e}")
        
        success_count = 0
        error_count = 0
        
        # Проверяем, есть ли обновленный текст (включая пустую строку, которая означает "без текста")
        has_new_text = "new_text" in message_data
        new_text = message_data.get("new_text")
        
        # Проверяем, есть ли оригинальный текст
        original_text = message_data.get("original_text")
        
        # Проверяем наличие медиа-контента
        photo_id = message_data.get("photo_id")
        video_id = message_data.get("video_id")
        document_id = message_data.get("document_id")
        audio_id = message_data.get("audio_id")
        voice_id = message_data.get("voice_id")
        caption = message_data.get("caption", "")
        
        # Определяем, есть ли медиа-контент
        has_media = any([photo_id, video_id, document_id, audio_id, voice_id])
        
        # Если есть и текст, и медиа, определяем, что отправлять
        if (has_new_text or original_text) and has_media:
            # Если есть и текст, и медиа, приоритет у медиа с текстом как caption
            self.logger.info("Обнаружен и текст, и медиа-контент. Отправляем медиа с текстом в качестве подписи.")
            
            # Определяем текст для подписи
            text_for_caption = ""
            if has_new_text and new_text is not None:
                text_for_caption = new_text
            elif original_text:
                text_for_caption = original_text
            
            # Ограничиваем длину подписи до 1024 символов (максимум для Telegram)
            if len(text_for_caption) > 1024:
                text_for_caption = text_for_caption[:1021] + "..."
            
            # Отправляем медиа с текстом как подписью
            if photo_id:
                with get_db() as db:
                    for user_id_batch in iter_broadcast_targets(db):
                        for user_id in user_id_batch:
                            try:
                                await self.bot.send_photo(
                                    chat_id=user_id,
                                    photo=photo_id,
                                    caption=text_for_caption,
                                    reply_markup=reply_markup
                                )
                                success_count += 1
                            except TelegramError as e:
                                error_count += 1
                                self.logger.warning(f"Ошибка отправки фото-рассылки пользователю {user_id}: {e}")
                                
                                if "bot was blocked" in str(e) or "user is deactivated" in str(e):
                                    pass
                            except Exception as e:
                                error_count += 1
                                self.logger.error(f"Неожиданная ошибка при отправке фото-рассылки пользователю {user_id}: {e}")
                            
                            await asyncio.sleep(0.05)  # 50 мс между батчами
            elif video_id:
                with get_db() as db:
                    for user_id_batch in iter_broadcast_targets(db):
                        for user_id in user_id_batch:
                            try:
                                await self.bot.send_video(
                                    chat_id=user_id,
                                    video=video_id,
                                    caption=text_for_caption,
                                    reply_markup=reply_markup
                                )
                                success_count += 1
                            except TelegramError as e:
                                error_count += 1
                                self.logger.warning(f"Ошибка отправки видео-рассылки пользователю {user_id}: {e}")
                                
                                if "bot was blocked" in str(e) or "user is deactivated" in str(e):
                                    pass
                            except Exception as e:
                                error_count += 1
                                self.logger.error(f"Неожиданная ошибка при отправке видео-рассылки пользователю {user_id}: {e}")
                            
                            await asyncio.sleep(0.05)  # 50 мс между батчами
            elif document_id:
                with get_db() as db:
                    for user_id_batch in iter_broadcast_targets(db):
                        for user_id in user_id_batch:
                            try:
                                await self.bot.send_document(
                                    chat_id=user_id,
                                    document=document_id,
                                    caption=text_for_caption,
                                    reply_markup=reply_markup
                                )
                                success_count += 1
                            except TelegramError as e:
                                error_count += 1
                                self.logger.warning(f"Ошибка отправки документ-рассылки пользователю {user_id}: {e}")
                                
                                if "bot was blocked" in str(e) or "user is deactivated" in str(e):
                                    pass
                            except Exception as e:
                                error_count += 1
                                self.logger.error(f"Неожиданная ошибка при отправке документ-рассылки пользователю {user_id}: {e}")
                            
                            await asyncio.sleep(0.05)  # 50 мс между батчами
            elif audio_id:
                with get_db() as db:
                    for user_id_batch in iter_broadcast_targets(db):
                        for user_id in user_id_batch:
                            try:
                                await self.bot.send_audio(
                                    chat_id=user_id,
                                    audio=audio_id,
                                    caption=text_for_caption,
                                    reply_markup=reply_markup
                                )
                                success_count += 1
                            except TelegramError as e:
                                error_count += 1
                                self.logger.warning(f"Ошибка отправки аудио-рассылки пользователю {user_id}: {e}")
                                
                                if "bot was blocked" in str(e) or "user is deactivated" in str(e):
                                    pass
                            except Exception as e:
                                error_count += 1
                                self.logger.error(f"Неожиданная ошибка при отправке аудио-рассылки пользователю {user_id}: {e}")
                            
                            await asyncio.sleep(0.05)  # 50 мс между батчами
            elif voice_id:
                with get_db() as db:
                    for user_id_batch in iter_broadcast_targets(db):
                        for user_id in user_id_batch:
                            try:
                                await self.bot.send_voice(
                                    chat_id=user_id,
                                    voice=voice_id,
                                    reply_markup=reply_markup
                                )
                                success_count += 1
                                
                                # Для голосовых сообщений подпись отправляем отдельным сообщением
                                if text_for_caption:
                                    await self.bot.send_message(
                                        chat_id=user_id,
                                        text=text_for_caption
                                    )
                            except TelegramError as e:
                                error_count += 1
                                self.logger.warning(f"Ошибка отправки голосовой рассылки пользователю {user_id}: {e}")
                                
                                if "bot was blocked" in str(e) or "user is deactivated" in str(e):
                                    pass
                            except Exception as e:
                                error_count += 1
                                self.logger.error(f"Неожиданная ошибка при отправке голосовой рассылки пользователю {user_id}: {e}")
                            
                            await asyncio.sleep(0.05)  # 50 мс между батчами
        elif has_new_text and new_text is not None:
            # Если есть только обновленный текст
            self.logger.info(f"Обнаружен new_text: '{new_text[:50]}...' (длина: {len(new_text) if new_text else 0})")
            if new_text: # Если new_text не пустой
                with get_db() as db:
                    for user_id_batch in iter_broadcast_targets(db):
                        # Отправляем сообщения в этой батч
                        for user_id in user_id_batch:
                            try:
                                await self.bot.send_message(
                                    chat_id=user_id,
                                    text=new_text,
                                    reply_markup=reply_markup
                                )
                                success_count += 1
                            except TelegramError as e:
                                error_count += 1
                                self.logger.warning(f"Ошибка отправки рассылки пользователю {user_id}: {e}")
                                
                                # Проверяем, заблокировал ли пользователь бота
                                if "bot was blocked" in str(e) or "user is deactivated" in str(e):
                                    # В реальной системе можно было бы обновить статус пользователя
                                    pass
                            except Exception as e:
                                error_count += 1
                                self.logger.error(f"Неожиданная ошибка при отправке рассылки пользователю {user_id}: {e}")
                        
                        # Делаем паузу между батчами, чтобы не превысить лимиты Telegram API
                        await asyncio.sleep(0.05)  # 50 мс между батчами
            else:
                self.logger.info("new_text пустой, текст отправляться не будет")
                # Если new_text пустой, то просто не отправляем текст, переходим к медиа или copy_message
        elif original_text:
            # Если есть только оригинальный текст
            self.logger.info(f"Обнаружен original_text: '{original_text[:50]}...' (длина: {len(original_text) if original_text else 0})")
            # Если есть оригинальный текст, отправляем его напрямую
            with get_db() as db:
                for user_id_batch in iter_broadcast_targets(db):
                    # Отправляем сообщения в этой батч
                    for user_id in user_id_batch:
                        try:
                            await self.bot.send_message(
                                chat_id=user_id,
                                text=original_text,
                                reply_markup=reply_markup
                            )
                            success_count += 1
                        except TelegramError as e:
                            error_count += 1
                            self.logger.warning(f"Ошибка отправки рассылки пользователю {user_id}: {e}")
                            
                            # Проверяем, заблокировал ли пользователь бота
                            if "bot was blocked" in str(e) or "user is deactivated" in str(e):
                                # В реальной системе можно было бы обновить статус пользователя
                                pass
                        except Exception as e:
                            error_count += 1
                            self.logger.error(f"Неожиданная ошибка при отправке рассылки пользователю {user_id}: {e}")
                        
                        # Делаем паузу между батчами, чтобы не превысить лимиты Telegram API
                        await asyncio.sleep(0.05)  # 50 мс между батчами
        elif has_media:
            # Если есть только медиа-контент
            self.logger.info("Обнаружен только медиа-контент, отправляем медиа с caption")
            
            # Определяем текст для подписи из caption
            text_for_caption = caption
            
            # Ограничиваем длину подписи до 1024 символов (максимум для Telegram)
            if len(text_for_caption) > 1024:
                text_for_caption = text_for_caption[:1021] + "..."
            
            if photo_id:
                with get_db() as db:
                    for user_id_batch in iter_broadcast_targets(db):
                        for user_id in user_id_batch:
                            try:
                                await self.bot.send_photo(
                                    chat_id=user_id,
                                    photo=photo_id,
                                    caption=text_for_caption,
                                    reply_markup=reply_markup
                                )
                                success_count += 1
                            except TelegramError as e:
                                error_count += 1
                                self.logger.warning(f"Ошибка отправки фото-рассылки пользователю {user_id}: {e}")
                                
                                if "bot was blocked" in str(e) or "user is deactivated" in str(e):
                                    pass
                            except Exception as e:
                                error_count += 1
                                self.logger.error(f"Неожиданная ошибка при отправке фото-рассылки пользователю {user_id}: {e}")
                            
                            await asyncio.sleep(0.05) # 50 мс между батчами
            elif video_id:
                with get_db() as db:
                    for user_id_batch in iter_broadcast_targets(db):
                        for user_id in user_id_batch:
                            try:
                                await self.bot.send_video(
                                    chat_id=user_id,
                                    video=video_id,
                                    caption=text_for_caption,
                                    reply_markup=reply_markup
                                )
                                success_count += 1
                            except TelegramError as e:
                                error_count += 1
                                self.logger.warning(f"Ошибка отправки видео-рассылки пользователю {user_id}: {e}")
                                
                                if "bot was blocked" in str(e) or "user is deactivated" in str(e):
                                    pass
                            except Exception as e:
                                error_count += 1
                                self.logger.error(f"Неожиданная ошибка при отправке видео-рассылки пользователю {user_id}: {e}")
                            
                            await asyncio.sleep(0.05) # 50 мс между батчами
            elif document_id:
                with get_db() as db:
                    for user_id_batch in iter_broadcast_targets(db):
                        for user_id in user_id_batch:
                            try:
                                await self.bot.send_document(
                                    chat_id=user_id,
                                    document=document_id,
                                    caption=text_for_caption,
                                    reply_markup=reply_markup
                                )
                                success_count += 1
                            except TelegramError as e:
                                error_count += 1
                                self.logger.warning(f"Ошибка отправки документ-рассылки пользователю {user_id}: {e}")
                                
                                if "bot was blocked" in str(e) or "user is deactivated" in str(e):
                                    pass
                            except Exception as e:
                                error_count += 1
                                self.logger.error(f"Неожиданная ошибка при отправке документ-рассылки пользователю {user_id}: {e}")
                                
                                await asyncio.sleep(0.05)  # 50 мс между батчами
            elif audio_id:
                with get_db() as db:
                    for user_id_batch in iter_broadcast_targets(db):
                        for user_id in user_id_batch:
                            try:
                                await self.bot.send_audio(
                                    chat_id=user_id,
                                    audio=audio_id,
                                    caption=text_for_caption,
                                    reply_markup=reply_markup
                                )
                                success_count += 1
                            except TelegramError as e:
                                error_count += 1
                                self.logger.warning(f"Ошибка отправки аудио-рассылки пользователю {user_id}: {e}")
                                
                                if "bot was blocked" in str(e) or "user is deactivated" in str(e):
                                    pass
                            except Exception as e:
                                error_count += 1
                                self.logger.error(f"Неожиданная ошибка при отправке аудио-рассылки пользователю {user_id}: {e}")
                            
                            await asyncio.sleep(0.05)  # 50 мс между батчами
            elif voice_id:
                with get_db() as db:
                    for user_id_batch in iter_broadcast_targets(db):
                        for user_id in user_id_batch:
                            try:
                                await self.bot.send_voice(
                                    chat_id=user_id,
                                    voice=voice_id,
                                    reply_markup=reply_markup
                                )
                                success_count += 1
                                
                                # Для голосовых сообщений подпись отправляем отдельным сообщением
                                if text_for_caption:
                                    await self.bot.send_message(
                                        chat_id=user_id,
                                        text=text_for_caption
                                    )
                            except TelegramError as e:
                                error_count += 1
                                self.logger.warning(f"Ошибка отправки голосовой рассылки пользователю {user_id}: {e}")
                                
                                if "bot was blocked" in str(e) or "user is deactivated" in str(e):
                                    pass
                            except Exception as e:
                                error_count += 1
                                self.logger.error(f"Неожиданная ошибка при отправке голосовой рассылки пользователю {user_id}: {e}")
                            
                            await asyncio.sleep(0.05) # 50 мс между батчами
        else:
            # Если нет ни текста, ни медиа, используем оригинальный метод (copy_message)
            # Получаем ID сообщения и чата
            message_id = message_data.get("message_id")
            source_chat_id = message_data.get("chat_id") or settings.ADMIN_CHAT_ID
            
            if not message_id:
                self.logger.error(f"Нет ID сообщения для рассылки {scheduled_broadcast.id}")
                return
            
            # Итерируем по пользователям и отправляем сообщение
            with get_db() as db:
                for user_id_batch in iter_broadcast_targets(db):
                    # Отправляем сообщения в этой батч
                    for user_id in user_id_batch:
                        try:
                            await self.bot.copy_message(
                                chat_id=user_id,
                                from_chat_id=source_chat_id,
                                message_id=message_id
                            )
                            success_count += 1
                        except TelegramError as e:
                            error_count += 1
                            self.logger.warning(f"Ошибка отправки рассылки пользователю {user_id}: {e}")
                            
                            # Проверяем, заблокировал ли пользователь бота
                            if "bot was blocked" in str(e) or "user is deactivated" in str(e):
                                # В реальной системе можно было бы обновить статус пользователя
                                pass
                        except Exception as e:
                            error_count += 1
                            self.logger.error(f"Неожиданная ошибка при отправке рассылки пользователю {user_id}: {e}")
                
                # Делаем паузу между батчами, чтобы не превысить лимиты Telegram API
                await asyncio.sleep(0.05)  # 50 мс между батчами
        
        self.logger.info(f"Отправка рассылки {scheduled_broadcast.id} завершена: {success_count} успешно, {error_count} с ошибками")
        
        # Отправляем уведомление администратору
        try:
            notifier = Notifier(self.bot)
            report_text = (
                f"✅ Отложена рассылка отправлена!\n\n"
                f"• Успешно: {success_count}\n"
                f"• Ошибки: {error_count}\n"
                f"• Время отправки: {scheduled_broadcast.scheduled_datetime}"
            )
            await notifier.send_admin_notification(report_text)
        except Exception as e:
            self.logger.error(f"Ошибка при отправке уведомления администратору: {e}")