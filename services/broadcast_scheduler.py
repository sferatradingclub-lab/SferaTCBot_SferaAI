import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from telegram import Bot
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from config import get_settings
from db_session import get_db
from models.crud import get_pending_scheduled_broadcasts, mark_broadcast_as_sent
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
        
        # Получаем ID сообщения и чата
        message_id = message_data.get("message_id")
        source_chat_id = message_data.get("chat_id") or settings.ADMIN_CHAT_ID
        
        if not message_id:
            self.logger.error(f"Нет ID сообщения для рассылки {scheduled_broadcast.id}")
            return
        
        # Итерируем по пользователям и отправляем сообщение
        success_count = 0
        error_count = 0
        
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