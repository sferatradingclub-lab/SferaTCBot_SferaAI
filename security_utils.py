"""Утилиты безопасности для SferaTC бота."""
import ipaddress
from typing import Optional
from fastapi import Request
from config import get_settings


def validate_telegram_webhook(request: Request) -> bool:
    """
    Проверяет, что запрос пришел от Telegram.
    
    Args:
        request: FastAPI Request объект
        
    Returns:
        bool: True если запрос валиден, False в противном случае
    """
    settings = get_settings()
    
    # Если установлен секретный токен, проверяем его
    if settings.WEBHOOK_SECRET_TOKEN:
        secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret_header != settings.WEBHOOK_SECRET_TOKEN:
            settings.logger.warning(f"Неверный секретный токен вебхука: {secret_header}")
            return False
        return True
    else:
        # Если секретный токен не установлен, проверяем IP-адрес
        # Telegram использует следующие IP-диапазоны: 149.154.160.0/20 и 91.108.4.0/22
        client_host = request.client.host if request.client else None
        if client_host:
            try:
                ip = ipaddress.IPv4Address(client_host)
                # Проверяем, находится ли IP в диапазонах Telegram
                telegram_networks = [
                    ipaddress.IPv4Network("149.154.160.0/20"),
                    ipaddress.IPv4Network("91.108.4.0/22")
                ]
                if any(ip in net for net in telegram_networks):
                    return True
                # Также проверяем локальные IP для отладки
                if ip.is_loopback or ip.is_private:
                    return True
            except ipaddress.AddressValueError:
                settings.logger.warning(f"Неверный формат IP-адреса: {client_host}")
        
        settings.logger.warning(f"Запрос с подозрительного IP-адреса: {client_host}")
        return False


def validate_update_data(update_data: dict) -> bool:
    """
    Проверяет, что данные обновления являются валидными.
    
    Args:
        update_data: Словарь с данными обновления
        
    Returns:
        bool: True если данные валидны, False в противном случае
    """
    if not isinstance(update_data, dict):
        return False
    
    # Проверяем наличие обязательного поля update_id
    if 'update_id' not in update_data:
        return False
    
    # Проверяем, что update_id - это число
    if not isinstance(update_data['update_id'], int):
        return False
    
    return True