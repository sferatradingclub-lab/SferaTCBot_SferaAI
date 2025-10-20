import logging
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, Union

from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class EnhancedErrorHandler:
    """Улучшенный обработчик ошибок с детальным логированием и уведомлениями."""
    
    def __init__(self):
        self.error_count = 0
        self.last_error_time = None
        self.critical_errors_count = 0
    
    async def handle_error(
        self, 
        error: Exception, 
        update: Optional[Update] = None,
        context: Optional[ContextTypes.DEFAULT_TYPE] = None,
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Централизованная обработка ошибок с детальным анализом."""
        
        now = datetime.now()
        self.error_count += 1
        self.last_error_time = now
        
        # Определяем тип ошибки
        error_type = self._classify_error(error)
        
        # Создаем детальную информацию об ошибке
        error_info = {
            "error_id": f"err_{now.strftime('%Y%m%d_%H%M%S')}_{self.error_count}",
            "error_type": error_type,
            "error_class": type(error).__name__,
            "error_message": str(error),
            "timestamp": now.isoformat(),
            "traceback": traceback.format_exc(),
            "is_critical": self._is_critical_error(error),
            "custom_message": custom_message
        }
        
        # Добавляем информацию об update если доступна
        if update:
            error_info["update_info"] = self._extract_update_info(update)
        
        # Добавляем информацию о контексте если доступна
        if context:
            error_info["context_info"] = self._extract_context_info(context)
        
        # Логируем ошибку соответствующим уровнем
        if error_info["is_critical"]:
            logger.critical(f"Критическая ошибка: {error_info}")
            self.critical_errors_count += 1
        else:
            logger.error(f"Ошибка: {error_info}")
        
        # Отправляем уведомление админу при критических ошибках
        if error_info["is_critical"] and context:
            await self._notify_admin_critical_error(error_info, context)
            
        return error_info
    
    def _classify_error(self, error: Exception) -> str:
        """Классифицирует тип ошибки."""
        error_class = type(error).__name__
        
        if isinstance(error, (ConnectionError, TimeoutError, OSError)):
            return "network_error"
        elif isinstance(error, (ValueError, TypeError)):
            return "data_error"
        elif isinstance(error, TelegramError):
            return "telegram_error"
        elif isinstance(error, (MemoryError, SystemError)):
            return "system_error"
        else:
            return "unknown_error"
    
    def _is_critical_error(self, error: Exception) -> bool:
        """Определяет является ли ошибка критической."""
        critical_errors = (
            ConnectionError,
            TimeoutError,
            OSError,
            RuntimeError,
            SystemError,
            MemoryError
        )
        return isinstance(error, critical_errors)
    
    def _extract_update_info(self, update: Update) -> Dict[str, Any]:
        """Извлекает информацию из Update объекта."""
        info = {
            "has_message": update.message is not None,
            "has_callback_query": update.callback_query is not None,
            "has_inline_query": update.inline_query is not None,
        }
        
        if update.effective_user:
            info["user"] = {
                "id": update.effective_user.id,
                "username": update.effective_user.username,
                "full_name": update.effective_user.full_name
            }
        
        if update.effective_chat:
            info["chat"] = {
                "id": update.effective_chat.id,
                "type": update.effective_chat.type
            }
        
        if update.message:
            info["message"] = {
                "text": update.message.text,
                "has_photo": update.message.photo is not None,
                "has_document": update.message.document is not None
            }
            
        return info
    
    def _extract_context_info(self, context: ContextTypes.DEFAULT_TYPE) -> Dict[str, Any]:
        """Извлекает информацию из Context объекта."""
        info = {
            "bot_data_keys": list(context.bot_data.keys()) if context.bot_data else [],
            "user_data_keys": list(context.user_data.keys()) if context.user_data else [],
        }
        
        if hasattr(context, 'chat_data') and context.chat_data:
            info["chat_data_keys"] = list(context.chat_data.keys())
            
        return info
    
    async def _notify_admin_critical_error(self, error_info: Dict, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет уведомление админу о критической ошибке."""
        try:
            from services.notifier import Notifier
            from config import get_settings
            
            settings = get_settings()
            if not settings.ADMIN_CHAT_ID:
                logger.error("ADMIN_CHAT_ID не настроен для отправки уведомлений")
                return
            
            notifier = Notifier(context.bot)
            
            # Сокращаем сообщение для избежания превышения лимита
            error_summary = (
                "🚨 Критическая ошибка в боте\n\n"
                f"Тип: {error_info['error_type']}\n"
                f"Класс: {error_info['error_class']}\n"
                f"Время: {error_info['timestamp']}\n"
            )
            
            if len(error_info['error_message']) > 500:
                error_summary += f"Сообщение: {error_info['error_message'][:500]}...\n"
            else:
                error_summary += f"Сообщение: {error_info['error_message']}\n"
            
            if error_info.get("update_info", {}).get("user"):
                user = error_info["update_info"]["user"]
                error_summary += f"Пользователь: {user['full_name']} (@{user['username']}) ID: {user['id']}\n"
            
            error_summary += f"\nОбщее количество ошибок: {self.error_count}"
            
            await notifier.send_admin_notification(
                error_summary,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            
            logger.info(f"Уведомление о критической ошибке отправлено админу")
            
        except Exception as notify_error:
            logger.error(f"Не удалось отправить уведомление админу: {notify_error}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Возвращает статистику ошибок."""
        return {
            "total_errors": self.error_count,
            "critical_errors": self.critical_errors_count,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "errors_per_hour": self._calculate_error_rate()
        }
    
    def _calculate_error_rate(self) -> float:
        """Вычисляет количество ошибок в час."""
        if not self.last_error_time:
            return 0.0
            
        hours_diff = (datetime.now() - self.last_error_time).total_seconds() / 3600
        if hours_diff == 0:
            return 0.0
            
        return self.error_count / hours_diff