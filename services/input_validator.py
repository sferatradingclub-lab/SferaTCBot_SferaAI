import re
import logging
from typing import Tuple, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class InputValidator:
    """Сервис для валидации и очистки пользовательского ввода."""
    
    # Константы
    MAX_MESSAGE_LENGTH = 4000
    MIN_MESSAGE_LENGTH = 1
    MAX_USERNAME_LENGTH = 32
    
    # Паттерны для фильтрации подозрительного контента
    SUSPICIOUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<\s*iframe',
        r'<\s*object',
        r'<\s*embed',
        r'<\s*link',
        r'<\s*meta',
        r'vbscript:',
        r'data:text/html',
    ]
    
    # Разрешенные домены для URL
    ALLOWED_DOMAINS = {
        'telegram.org', 'telegram.me', 't.me',
        'github.com', 'gitlab.com',
        'youtube.com', 'youtu.be',
        'tradingview.com'
    }
    
    @classmethod
    def validate_message(cls, text: str) -> Tuple[bool, str]:
        """Валидирует текстовое сообщение."""
        if not text:
            return False, "Сообщение пустое"
            
        text_stripped = text.strip()
        if len(text_stripped) < cls.MIN_MESSAGE_LENGTH:
            return False, "Сообщение слишком короткое"
            
        if len(text) > cls.MAX_MESSAGE_LENGTH:
            return False, f"Сообщение слишком длинное (максимум {cls.MAX_MESSAGE_LENGTH} символов)"
        
        # Проверка на подозрительный контент
        for pattern in cls.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                logger.warning(f"Обнаружен подозрительный контент: {pattern}")
                return False, "Обнаружен подозрительный контент"
                
        return True, "OK"
    
    @classmethod
    def validate_username(cls, username: str) -> Tuple[bool, str]:
        """Валидирует username пользователя."""
        if not username:
            return False, "Username пустой"
            
        if len(username) > cls.MAX_USERNAME_LENGTH:
            return False, f"Username слишком длинный (максимум {cls.MAX_USERNAME_LENGTH} символов)"
            
        # Проверка формата username (только буквы, цифры, подчеркивания)
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "Username содержит недопустимые символы"
            
        return True, "OK"
    
    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, str]:
        """Валидирует URL."""
        if not url:
            return True, "OK"  # Опциональные URL могут быть пустыми
            
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False, "Некорректный формат URL"
                
            if parsed.scheme not in ('http', 'https'):
                return False, "URL должен начинаться с http или https"
                
            # Проверка домена (простая проверка)
            domain = parsed.netloc.lower()
            if any(allowed in domain for allowed in cls.ALLOWED_DOMAINS):
                return True, "OK"
                
            # Для других доменов дополнительная проверка
            if len(domain) < 3 or len(domain) > 253:
                return False, "Некорректная длина домена"
                
            return True, "OK"
            
        except Exception as e:
            logger.error(f"Ошибка валидации URL {url}: {e}")
            return False, "Ошибка валидации URL"
    
    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Очищает текст от потенциально опасных символов."""
        if not text:
            return ""
            
        # Удаляем нулевые байты и управляющие символы
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        # Удаляем лишние пробелы
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Ограничиваем длину
        return sanitized[:cls.MAX_MESSAGE_LENGTH].strip()
    
    @classmethod
    def sanitize_username(cls, username: str) -> str:
        """Очищает username."""
        if not username:
            return ""
            
        # Удаляем все кроме букв, цифр и подчеркиваний
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '', username)
        
        return sanitized[:cls.MAX_USERNAME_LENGTH].strip()