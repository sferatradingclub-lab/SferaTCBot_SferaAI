"""
Error handling decorator for SferaAI tool functions.
Provides centralized error handling with logging and graceful degradation.
"""

import logging
import functools
from typing import Callable, Any
import traceback

logger = logging.getLogger(__name__)


def handle_tool_error(
    default_response: str = "Произошла ошибка при выполнении операции.",
    log_traceback: bool = True
):
    """
    Decorator for tool functions to handle errors gracefully.
    
    Args:
        default_response: Default error message to return
        log_traceback: Whether to log full traceback
        
    Usage:
        @handle_tool_error()
        async def my_tool(context, param1, param2):
            # tool code
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Log the error
                error_msg = f"Error in tool '{func.__name__}': {str(e)}"
                logger.error(error_msg)
                
                if log_traceback:
                    logger.error(f"Traceback:\n{traceback.format_exc()}")
                
                # Return user-friendly error message
                return f"{default_response} Детали: {str(e)}"
        
        return wrapper
    return decorator


def handle_tool_error_silent(fallback_value: Any = None):
    """
    Decorator that suppresses errors and returns a fallback value.
    Use for non-critical operations where failure should not interrupt flow.
    
    Args:
        fallback_value: Value to return on error
        
    Usage:
        @handle_tool_error_silent(fallback_value="")
        async def optional_tool(context, param):
            # tool code
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Silently handled error in '{func.__name__}': {str(e)}")
                return fallback_value
        
        return wrapper
    return decorator
