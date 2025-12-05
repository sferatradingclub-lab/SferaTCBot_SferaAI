"""
Система централизованной обработки ошибок для Sfera AI Agent
Обеспечивает единообразную обработку различных типов ошибок
"""

import logging
import traceback
import asyncio
from typing import Dict, Any, Optional, Callable
from functools import wraps
from enum import Enum
import json
from datetime import datetime


class ErrorSeverity(Enum):
    """Уровни серьезности ошибок"""
    LOW = "low"           # Предупреждения, не критичные
    MEDIUM = "medium"     # Ошибки, требующие внимания
    HIGH = "high"         # Критические ошибки
    CRITICAL = "critical" # Ошибки, приводящие к сбою системы


class ErrorType(Enum):
    """Типы ошибок в системе"""
    MEMORY_ERROR = "memory_error"
    LLM_ERROR = "llm_error"
    NETWORK_ERROR = "network_error"
    CONFIGURATION_ERROR = "configuration_error"
    TOOL_ERROR = "tool_error"
    DATABASE_ERROR = "database_error"
    UNKNOWN_ERROR = "unknown_error"


class SferaAIError(Exception):
    """Базовый класс исключений Sfera AI"""
    
    def __init__(
        self, 
        message: str, 
        error_type: ErrorType = ErrorType.UNKNOWN_ERROR,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.message = message
        self.error_type = error_type
        self.severity = severity
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.utcnow().isoformat()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование ошибки в словарь для логирования"""
        return {
            "type": self.error_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
            "traceback": traceback.format_exc() if self.cause else None
        }


class MemoryError(SferaAIError):
    """Ошибки системы памяти"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorType.MEMORY_ERROR, 
            ErrorSeverity.HIGH, 
            details
        )


class LLMError(SferaAIError):
    """Ошибки языковой модели"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorType.LLM_ERROR, 
            ErrorSeverity.HIGH, 
            details
        )


class NetworkError(SferaAIError):
    """Сетевые ошибки"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorType.NETWORK_ERROR, 
            ErrorSeverity.MEDIUM, 
            details
        )


class ConfigurationError(SferaAIError):
    """Ошибки конфигурации"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorType.CONFIGURATION_ERROR, 
            ErrorSeverity.CRITICAL, 
            details
        )


class ToolError(SferaAIError):
    """Ошибки инструментов"""
    def __init__(self, message: str, tool_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorType.TOOL_ERROR, 
            ErrorSeverity.MEDIUM, 
            {**details or {}, "tool_name": tool_name}
        )


class DatabaseError(SferaAIError):
    """Ошибки базы данных"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorType.DATABASE_ERROR, 
            ErrorSeverity.HIGH, 
            details
        )


class ErrorHandler:
    """Централизованный обработчик ошибок"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_counts: Dict[str, int] = {}
        self.error_callbacks: Dict[ErrorType, Callable] = {}
        
        # Настройка логгера для ошибок
        self._setup_error_logger()
    
    def _setup_error_logger(self):
        """Настройка специального логгера для ошибок"""
        error_handler = logging.StreamHandler()
        error_handler.setLevel(logging.ERROR)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        error_handler.setFormatter(formatter)
        
        self.logger.addHandler(error_handler)
        self.logger.setLevel(logging.ERROR)
    
    def register_callback(self, error_type: ErrorType, callback: Callable):
        """Регистрация колбэка для конкретного типа ошибки"""
        self.error_callbacks[error_type] = callback
    
    def handle_error(
        self, 
        error: Exception, 
        context: Optional[str] = None,
        reraise: bool = True
    ) -> Optional[SferaAIError]:
        """Централизованная обработка ошибок"""
        
        # Преобразование в SferaAIError если нужно
        if isinstance(error, SferaAIError):
            sfera_error = error
        else:
            # Определяем тип ошибки по исключению
            error_type = self._classify_error(error)
            severity = self._determine_severity(error)
            
            sfera_error = SferaAIError(
                message=str(error),
                error_type=error_type,
                severity=severity,
                details={"original_exception": type(error).__name__},
                cause=error
            )
        
        # Добавляем контекст если указан
        if context:
            sfera_error.details["context"] = context
        
        # Логируем ошибку
        self._log_error(sfera_error)
        
        # Обновляем счетчики
        self._update_error_counts(sfera_error)
        
        # Выполняем колбэк если зарегистрирован
        if sfera_error.error_type in self.error_callbacks:
            try:
                self.error_callbacks[sfera_error.error_type](sfera_error)
            except Exception as callback_error:
                self.logger.error(f"Error in error callback: {callback_error}")
        
        # Повторно выбрасываем если нужно
        if reraise:
            raise sfera_error
        
        return sfera_error
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Классификация типа ошибки по исключению"""
        error_name = type(error).__name__.lower()
        
        if any(keyword in error_name for keyword in ['memory', 'qdrant']):
            return ErrorType.MEMORY_ERROR
        elif any(keyword in error_name for keyword in ['llm', 'gemini', 'openai']):
            return ErrorType.LLM_ERROR
        elif any(keyword in error_name for keyword in ['network', 'connection', 'timeout']):
            return ErrorType.NETWORK_ERROR
        elif any(keyword in error_name for keyword in ['config', 'environment']):
            return ErrorType.CONFIGURATION_ERROR
        elif any(keyword in error_name for keyword in ['tool', 'search', 'weather']):
            return ErrorType.TOOL_ERROR
        elif any(keyword in error_name for keyword in ['database', 'db', 'sql']):
            return ErrorType.DATABASE_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
    
    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """Определение серьезности ошибки"""
        error_name = type(error).__name__.lower()
        
        if any(keyword in error_name for keyword in ['critical', 'fatal', 'system']):
            return ErrorSeverity.CRITICAL
        elif any(keyword in error_name for keyword in ['memory', 'llm', 'database']):
            return ErrorSeverity.HIGH
        elif any(keyword in error_name for keyword in ['network', 'timeout']):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _log_error(self, error: SferaAIError):
        """Логирование ошибки с подробной информацией"""
        log_message = f"[{error.error_type.value.upper()}] {error.message}"
        
        if error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.error(log_message)
            self.logger.error(f"Details: {json.dumps(error.details, indent=2)}")
            if error.cause:
                self.logger.error(f"Caused by: {error.cause}")
        else:
            self.logger.warning(log_message)
    
    def _update_error_counts(self, error: SferaAIError):
        """Обновление счетчиков ошибок"""
        error_key = f"{error.error_type.value}_{error.severity.value}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Получение статистики ошибок"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_breakdown": self.error_counts.copy(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def should_alert(self, error: SferaAIError) -> bool:
        """Определение необходимости алерта"""
        # Алерт для критических ошибок или частых ошибок
        if error.severity == ErrorSeverity.CRITICAL:
            return True
        
        # Алерт если ошибка повторяется часто
        error_key = f"{error.error_type.value}_{error.severity.value}"
        count = self.error_counts.get(error_key, 0)
        
        if error.severity == ErrorSeverity.HIGH and count >= 5:
            return True
        elif error.severity == ErrorSeverity.MEDIUM and count >= 10:
            return True
        
        return False


# Глобальный экземпляр обработчика ошибок
error_handler = ErrorHandler()


def handle_errors(
    reraise: bool = True,
    context: Optional[str] = None,
    fallback_return: Any = None
):
    """Декоратор для автоматической обработки ошибок"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error = error_handler.handle_error(
                    e, 
                    context=f"{func.__name__}: {context}" if context else func.__name__,
                    reraise=False
                )
                if reraise:
                    raise error
                return fallback_return
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error = error_handler.handle_error(
                    e, 
                    context=f"{func.__name__}: {context}" if context else func.__name__,
                    reraise=False
                )
                if reraise:
                    raise error
                return fallback_return
        
        # Определяем какой враппер использовать
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Предопределенные колбэки для различных типов ошибок
def setup_error_callbacks():
    """Настройка колбэков для обработки специфичных ошибок"""
    
    @error_handler.register_callback(ErrorType.MEMORY_ERROR)
    def handle_memory_error(error: SferaAIError):
        """Обработка ошибок памяти"""
        # Можно добавить логику восстановления памяти
        logging.warning(f"Memory error occurred: {error.message}")
    
    @error_handler.register_callback(ErrorType.LLM_ERROR)
    def handle_llm_error(error: SferaAIError):
        """Обработка ошибок LLM"""
        # Можно добавить логику переключения модели или fallback
        logging.warning(f"LLM error occurred: {error.message}")
    
    @error_handler.register_callback(ErrorType.CONFIGURATION_ERROR)
    def handle_config_error(error: SferaAIError):
        """Обработка ошибок конфигурации"""
        # Критические ошибки конфигурации требуют немедленного внимания
        logging.critical(f"Configuration error: {error.message}")
    
    @error_handler.register_callback(ErrorType.TOOL_ERROR)
    def handle_tool_error(error: SferaAIError):
        """Обработка ошибок инструментов"""
        tool_name = error.details.get("tool_name", "unknown")
        logging.warning(f"Tool '{tool_name}' error: {error.message}")


# Инициализация колбэков при импорте
setup_error_callbacks()


# Утилиты для работы с ошибками
def create_safe_async_function(func: Callable) -> Callable:
    """Создание безопасной асинхронной функции с обработкой ошибок"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_handler.handle_error(e, context=f"safe_{func.__name__}")
            return None
    
    return wrapper


def retry_with_backoff(
    max_attempts: int = 3,
    backoff_factor: float = 1.0,
    exceptions: tuple = (Exception,)
):
    """Декоратор для повторных попыток с экспоненциальным бэк-офф"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = backoff_factor * (2 ** attempt)
                        logging.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}, "
                            f"retrying in {wait_time}s: {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        error_handler.handle_error(
                            e, 
                            context=f"retry_{func.__name__}_failed_after_{max_attempts}_attempts"
                        )
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = backoff_factor * (2 ** attempt)
                        logging.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}, "
                            f"retrying in {wait_time}s: {e}"
                        )
                        import time
                        time.sleep(wait_time)
                    else:
                        error_handler.handle_error(
                            e, 
                            context=f"retry_{func.__name__}_failed_after_{max_attempts}_attempts"
                        )
            
            raise last_exception
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


if __name__ == "__main__":
    # Тестирование системы обработки ошибок
    
    # Тест создания специфичных ошибок
    try:
        raise MemoryError("Тест ошибки памяти", {"user_id": "test"})
    except SferaAIError as e:
        print(f"Caught memory error: {e.message}")
        print(f"Error type: {e.error_type.value}")
        print(f"Severity: {e.severity.value}")
    
    # Тест декоратора
    @handle_errors(reraise=False, fallback_return="fallback_result")
    def test_function():
        raise ValueError("Тест ошибки")
    
    result = test_function()
    print(f"Function result: {result}")
    
    # Получение статистики
    stats = error_handler.get_error_stats()
    print(f"Error stats: {stats}")