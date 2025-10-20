"""Unified notifier service for user and admin communications."""

from __future__ import annotations

from typing import Optional, Union

from telegram import Bot, Message
from telegram.error import TelegramError
from telegram.ext import ExtBot

from config import get_settings


class Notifier:
    """Centralized helper for delivering Telegram notifications."""

    def __init__(self, bot: Union[Bot, ExtBot]) -> None:
        self._bot = bot
        self._settings = get_settings()
        self._logger = self._settings.logger

    async def send_message(
        self, chat_id: int, text: str, **kwargs
    ) -> Optional[Message]:
        """Safely sends a message to a Telegram chat."""

        if self._bot is None:
            self._logger.error("Попытка отправить сообщение без инициализированного бота.")
            return None

        try:
            return await self._bot.send_message(chat_id=chat_id, text=text, **kwargs)
        except TelegramError as error:
            self._logger.warning(
                "Не удалось отправить сообщение в чат %s: %s",
                chat_id,
                error,
            )
            return None

    async def send_admin_notification(self, text: str, **kwargs) -> Optional[Message]:
        """Sends a notification to the configured administrator chat."""
        
        admin_chat_id = self._settings.ADMIN_CHAT_ID
        if not admin_chat_id:
            self._logger.error("ADMIN_CHAT_ID не настроен. Невозможно отправить уведомление админу.")
            return None
        
        try:
            resolved_chat_id = int(admin_chat_id)
            self._logger.info(f"Попытка отправить админ-уведомление в чат {resolved_chat_id}")
        except (TypeError, ValueError) as e:
            self._logger.error(
                f"ADMIN_CHAT_ID имеет некорректный формат: {admin_chat_id}. Ошибка: {e}"
            )
            return None
        
        # Ограничиваем длину сообщения для Telegram
        max_length = 4000  # Оставляем запас от лимита 4096
        if len(text) > max_length:
            # Разбиваем длинное сообщение на части
            text_parts = [text[i:i+max_length] for i in range(0, len(text), max_length)]
            self._logger.info(f"Сообщение разбито на {len(text_parts)} частей")
            
            for i, part in enumerate(text_parts):
                part_text = f"Часть {i+1}/{len(text_parts)}:\n{part}"
                self._logger.info(f"Вызов send_message для админ-уведомления в чат {resolved_chat_id}, часть {i+1}")
                result = await self.send_message(resolved_chat_id, part_text, **kwargs)
                
                if result is None:
                    self._logger.error(f"send_message вернул None для админ-уведомления в чат {resolved_chat_id}, часть {i+1}")
                else:
                    self._logger.info(f"Админ-уведомление успешно отправлено в чат {resolved_chat_id}, часть {i+1}, Message ID: {result.message_id}")
            
            return result  # Возвращаем результат последней отправки
        else:
            # Обычная отправка короткого сообщения
            self._logger.info(f"Вызов send_message для админ-уведомления в чат {resolved_chat_id}")
            result = await self.send_message(resolved_chat_id, text, **kwargs)
            
            if result is None:
                self._logger.error(f"send_message вернул None для админ-уведомления в чат {resolved_chat_id}")
            else:
                self._logger.info(f"Админ-уведомление успешно отправлено в чат {resolved_chat_id}, Message ID: {result.message_id}")
                
            return result


__all__ = ["Notifier"]
