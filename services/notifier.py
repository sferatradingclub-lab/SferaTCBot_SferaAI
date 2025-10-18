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
        except (TypeError, ValueError):
            self._logger.error(
                "ADMIN_CHAT_ID имеет некорректный формат: %s", admin_chat_id
            )
            return None

        return await self.send_message(resolved_chat_id, text, **kwargs)


__all__ = ["Notifier"]
