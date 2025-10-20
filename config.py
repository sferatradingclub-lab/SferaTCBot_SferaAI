from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import ClassVar, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Application configuration loaded from environment variables."""

    DEFAULT_CHATGPT_FREE_MODELS: ClassVar[List[str]] = [
        "deepseek/deepseek-r1-0528-qwen3-8b:free",
        "z-ai/glm-4.5-air:free",
    ]

    CHATGPT_BASE_URL: str = field(default="https://openrouter.ai/api/v1", init=False)

    logger: logging.Logger = field(init=False)
    LOG_TO_FILE: bool = field(init=False)
    LOG_FILE_PATH: str = field(init=False)

    _TELEGRAM_TOKEN: str = field(init=False, repr=False)
    BOT_USERNAME: str = field(init=False)
    _ADMIN_CHAT_ID: str = field(init=False, repr=False)
    
    @property
    def TELEGRAM_TOKEN(self) -> str:
        """Возвращает токен Telegram бота."""
        return self._TELEGRAM_TOKEN
        
    @property
    def ADMIN_CHAT_ID(self) -> str:
        """Возвращает ID администратора."""
        return self._ADMIN_CHAT_ID

    WEBHOOK_URL: Optional[str] = field(init=False)
    WEBHOOK_LISTEN: str = field(init=False)
    WEBHOOK_PORT: int = field(init=False)
    WEBHOOK_PATH: str = field(init=False)
    _WEBHOOK_SECRET_TOKEN: Optional[str] = field(init=False, repr=False)
    WEBHOOK_DROP_PENDING_UPDATES: bool = field(init=False)
    
    @property
    def WEBHOOK_SECRET_TOKEN(self) -> Optional[str]:
        """Возвращает секретный токен вебхука."""
        return self._WEBHOOK_SECRET_TOKEN

    DATABASE_URL: str = field(init=False)

    CHATGPT_MODELS: List[str] = field(init=False)
    DISCARDED_PAID_MODELS: List[str] = field(init=False)
    _OPENROUTER_API_KEY: Optional[str] = field(init=False, repr=False)
    
    @property
    def OPENROUTER_API_KEY(self) -> Optional[str]:
        """Возвращает API ключ OpenRouter."""
        return self._OPENROUTER_API_KEY

    STREAM_EDIT_INTERVAL_SECONDS: float = field(init=False)
    STREAM_BUFFER_SIZE_WORDS: int = field(init=False)
    
    # Параметры кеширования
    CACHE_TTL_MINUTES: int = field(init=False)
    MAX_CACHE_SIZE: int = field(init=False)

    TRAINING_BOT_URL: str = field(
        default="https://chatgpt.com/g/g-68d9b0f1d07c8191bba533ecfb9d1689-sferatc-lessons",
        init=False,
    )
    AI_PSYCHOLOGIST_URL: str = field(
        default="https://chatgpt.com/g/g-68bb703f9a3881918d51f97375d7d128-sferatc-ai",
        init=False,
    )
    FULL_COURSE_URL: str = field(
        default="https://g-2NaO34S37-sferatc-full-course",
        init=False,
    )
    TELEGRAM_CHANNEL_URL: str = field(default="https://t.me/SferaTC", init=False)

    WELCOME_IMAGE_URL: Optional[str] = field(init=False)
    TRAINING_IMAGE_URL: Optional[str] = field(init=False)
    PSYCHOLOGIST_IMAGE_URL: Optional[str] = field(init=False)
    CHATGPT_IMAGE_URL: Optional[str] = field(init=False)
    SUPPORT_IMAGE_URL: Optional[str] = field(init=False)
    TOOLS_IMAGE_URL: Optional[str] = field(init=False)

    BOT_KNOWLEDGE_BASE: str = field(init=False)
    SUPPORT_LLM_SYSTEM_PROMPT: str = field(init=False)
    SUPPORT_ESCALATION_BUTTON_TEXT: str = field(default="Позвать администратора", init=False)
    SUPPORT_ESCALATION_CALLBACK: str = field(default="support_llm_escalate", init=False)
    SUPPORT_LLM_HISTORY_LIMIT: int = field(default=10, init=False)

    TOOLS_DATA: Dict[str, Dict[str, object]] = field(init=False)

    def __post_init__(self) -> None:
        self.LOG_TO_FILE = self._env_flag("LOG_TO_FILE", default=False)
        self.LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "bot.log")
        self.logger = self._configure_logging()

        # Улучшенная валидация без внешних зависимостей
        self._validate_core_settings()
        self._load_core_settings()
        self._load_webhook_settings()
        self._load_database_settings()
        self._load_chatgpt_settings()
        self._load_image_urls()
        self._load_tools_settings()
        self._load_support_settings()
        self._load_streaming_settings()
        self._load_cache_settings()
        self._emit_warnings()

    def _validate_core_settings(self) -> None:
        """Валидация критически важных настроек без внешних библиотек."""
        required_vars = {
            "TELEGRAM_TOKEN": os.getenv("TELEGRAM_TOKEN"),
            "ADMIN_CHAT_ID": os.getenv("ADMIN_CHAT_ID"),
        }
        
        missing = [name for name, value in required_vars.items() if not value]
        if missing:
            message = f"Отсутствуют обязательные переменные окружения: {', '.join(missing)}"
            self.logger.critical(message)
            raise ValueError(message)
        
        # Валидация формата токена
        token = required_vars["TELEGRAM_TOKEN"]
        if not self._validate_telegram_token(token):
            raise ValueError("Некорректный формат токена Telegram")
        
        # Валидация ID админа
        admin_id = required_vars["ADMIN_CHAT_ID"]
        if not self._validate_admin_chat_id(admin_id):
            raise ValueError("Некорректный формат ADMIN_CHAT_ID")

    @staticmethod
    def _validate_telegram_token(token: str) -> bool:
        """Валидация токена Telegram без внешних библиотек."""
        if not token or len(token) < 35:
            return False
        # Формат: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
        pattern = r'^\d+:[A-Za-z0-9_-]{35,}$'
        return bool(re.match(pattern, token))

    @staticmethod
    def _validate_admin_chat_id(chat_id: str) -> bool:
        """Валидация ID чата администратора."""
        try:
            int(chat_id)
            return True
        except ValueError:
            return False

    @staticmethod
    def _validate_url(url: str) -> bool:
        """Валидация URL без внешних библиотек."""
        if not url:
            return True  # Опциональные URL могут быть пустыми
        
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Простая проверка домена
        if '://' in url:
            domain_part = url.split('://', 1)[1]
            if '/' in domain_part:
                domain_part = domain_part.split('/', 1)[0]
            return len(domain_part) > 0
        
        return False

    # ------------------------------------------------------------------
    # Loading helpers
    # ------------------------------------------------------------------
    def _load_core_settings(self) -> None:
        token = os.getenv("TELEGRAM_TOKEN")
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")

        missing: List[str] = []
        if not token:
            missing.append("TELEGRAM_TOKEN")
        if not admin_chat_id:
            missing.append("ADMIN_CHAT_ID")

        if missing:
            message = (
                "Отсутствуют обязательные переменные окружения: "
                + ", ".join(missing)
            )
            self.logger.critical(message)
            raise ValueError(message)

        self._TELEGRAM_TOKEN = token
        self._ADMIN_CHAT_ID = admin_chat_id
        self.BOT_USERNAME = os.getenv("BOT_USERNAME", "SferaTC_bot")

    def _load_webhook_settings(self) -> None:
        self.WEBHOOK_URL = self._normalize_webhook_url(os.getenv("WEBHOOK_URL"))
        self.WEBHOOK_LISTEN = os.getenv("WEBHOOK_LISTEN", "0.0.0.0")
        self.WEBHOOK_PORT = self._resolve_webhook_port()
        self.WEBHOOK_PATH = self._resolve_webhook_path(
            self.TELEGRAM_TOKEN, os.getenv("WEBHOOK_PATH")
        )
        secret = os.getenv("WEBHOOK_SECRET_TOKEN")
        self._WEBHOOK_SECRET_TOKEN = secret.strip() if secret else None
        self.WEBHOOK_DROP_PENDING_UPDATES = self._env_flag(
            "WEBHOOK_DROP_PENDING_UPDATES", default=True
        )

    def _load_database_settings(self) -> None:
        """Загрузка настроек базы данных с валидацией."""
        db_url = os.getenv("DATABASE_URL", "sqlite:///./sferatc_dev.db")
        
        # Валидация URL базы данных
        if not self._validate_database_url(db_url):
            raise ValueError(f"Некорректный DATABASE_URL: {db_url}")
        
        self.DATABASE_URL = db_url

    def _load_chatgpt_settings(self) -> None:
        raw_models = [
            os.getenv("CHATGPT_MODEL_PRIMARY", self.DEFAULT_CHATGPT_FREE_MODELS[0]),
            os.getenv("CHATGPT_MODEL_FALLBACK", self.DEFAULT_CHATGPT_FREE_MODELS[1]),
        ]
        free_models, discarded = self._ensure_free_models(raw_models)
        self.CHATGPT_MODELS = free_models
        self.DISCARDED_PAID_MODELS = discarded
        self._OPENROUTER_API_KEY = self._read_optional("OPENROUTER_API_KEY")

    def _load_image_urls(self) -> None:
        """Загрузка URL изображений с валидацией."""
        urls = {
            "WELCOME_IMAGE_URL": os.getenv("WELCOME_IMAGE_URL"),
            "TRAINING_IMAGE_URL": os.getenv("TRAINING_IMAGE_URL"),
            "PSYCHOLOGIST_IMAGE_URL": os.getenv("PSYCHOLOGIST_IMAGE_URL"),
            "CHATGPT_IMAGE_URL": os.getenv("CHATGPT_IMAGE_URL"),
            "SUPPORT_IMAGE_URL": os.getenv("SUPPORT_IMAGE_URL"),
            "TOOLS_IMAGE_URL": os.getenv("TOOLS_IMAGE_URL"),
        }
        
        for name, url in urls.items():
            if url and not self._validate_url(url):
                raise ValueError(f"Некорректный {name}: {url}")
        
        self.WELCOME_IMAGE_URL = urls["WELCOME_IMAGE_URL"]
        self.TRAINING_IMAGE_URL = urls["TRAINING_IMAGE_URL"]
        self.PSYCHOLOGIST_IMAGE_URL = urls["PSYCHOLOGIST_IMAGE_URL"]
        self.CHATGPT_IMAGE_URL = urls["CHATGPT_IMAGE_URL"]
        self.SUPPORT_IMAGE_URL = urls["SUPPORT_IMAGE_URL"]
        self.TOOLS_IMAGE_URL = urls["TOOLS_IMAGE_URL"]

    def _load_tools_settings(self) -> None:
        self.TOOLS_DATA = {
            "discounts": {
                "title": "💰 Скидки на комиссии",
                "intro_text": (
                    "В этом разделе собраны лучшие биржи и брокеры. Откройте счет по этим "
                    "ссылкам, чтобы получить максимальные скидки и экономить на комиссиях!"
                ),
                "items": [
                    {
                        "name": "Крипто Брокер Tiger.com",
                        "callback": "tool_tiger",
                        "description": (
                            "Единая платформа для торговли на нескольких биржах. Экономьте на "
                            "комиссиях, ведите автоматический дневник сделок и управляйте "
                            "рисками."
                        ),
                        "image_url": self._read_optional("TIGER_IMAGE_URL"),
                        "site_url": "https://account.tiger.com/signup?referral=sferatc",
                        "video_url": "https://www.youtube.com/@sferaTC",
                    },
                    {
                        "name": "Крипто Брокер Vataga Crypto",
                        "callback": "tool_vataga",
                        "description": (
                            "Торгуйте на всех крупных биржах через одну платформу: продвинутые "
                            "графики, мультиаккаунт и круглосуточная поддержка."
                        ),
                        "image_url": self._read_optional("VATAGA_IMAGE_URL"),
                        "site_url": "https://app.vataga.trading/register",
                        "video_url": "https://www.youtube.com/@sferaTC",
                    },
                    {
                        "name": "Крипто Брокер Whitelist",
                        "callback": "tool_whitelist",
                        "description": (
                            "Онлайн-офис для скальперов с мощным торговым терминалом Scalpee "
                            "для ПК и большим сообществом трейдеров."
                        ),
                        "image_url": self._read_optional("WHITELIST_IMAGE_URL"),
                        "site_url": "https://passport.whitelist.capital/signup/?ref=sferatc",
                        "video_url": "https://www.youtube.com/@sferaTC",
                    },
                ],
            },
            "screeners": {
                "title": "📈 Скринеры",
                "intro_text": "Выберите скринер:",
                "items": [],
            },
            "terminals": {
                "title": "🖥️ Торговые терминалы",
                "intro_text": "Выберите терминал:",
                "items": [],
            },
            "ping": {
                "title": "⚡️ Снизить ping",
                "intro_text": "Выберите сервис:",
                "items": [],
            },
        }

    def _load_support_settings(self) -> None:
        self.BOT_KNOWLEDGE_BASE = os.getenv(
            "BOT_KNOWLEDGE_BASE", "Информация о функциях бота не загружена."
        )
        self.SUPPORT_LLM_SYSTEM_PROMPT = (
            "Ты — ИИ-агент поддержки Telegram-бота SferaTC Bot. Твоя главная задача — "
            "точно и по делу помогать пользователям, основываясь на реальных функциях "
            "бота, описанных ниже. "
            "Не придумывай функции, которых нет. Всегда ссылайся на названия кнопок. "
            "Будь кратким и веди пользователя по шагам (на какую кнопку нажать).\n\n"
            "Вот актуальное описание функций бота:\n"
            f"{self.BOT_KNOWLEDGE_BASE}\n\n"
            "Если ты не знаешь ответа на вопрос, честно скажи об этом и предложи позвать "
            "администратора, нажав на кнопку 'Позвать администратора'."
        )

    def _load_streaming_settings(self) -> None:
        default_interval = 1.5
        raw_interval = os.getenv("STREAM_EDIT_INTERVAL_SECONDS")
        interval_value = default_interval
        if raw_interval is not None and raw_interval.strip():
            try:
                parsed_interval = float(raw_interval)
                if parsed_interval <= 0:
                    raise ValueError("Интервал должен быть положительным")
            except ValueError:
                self.logger.warning(
                    "Некорректное значение STREAM_EDIT_INTERVAL_SECONDS='%s'. Использую %s.",
                    raw_interval,
                    default_interval,
                )
            else:
                interval_value = parsed_interval

        default_buffer_size = 20
        raw_buffer_size = os.getenv("STREAM_BUFFER_SIZE_WORDS")
        buffer_size_value = default_buffer_size
        if raw_buffer_size is not None and raw_buffer_size.strip():
            try:
                parsed_buffer_size = int(raw_buffer_size)
                if parsed_buffer_size <= 0:
                    raise ValueError("Размер буфера должен быть положительным")
            except ValueError:
                self.logger.warning(
                    "Некорректное значение STREAM_BUFFER_SIZE_WORDS='%s'. Использую %s.",
                    raw_buffer_size,
                    default_buffer_size,
                )
            else:
                buffer_size_value = parsed_buffer_size

        self.STREAM_EDIT_INTERVAL_SECONDS = interval_value
        self.STREAM_BUFFER_SIZE_WORDS = buffer_size_value

    def _load_cache_settings(self) -> None:
        """Загрузка настроек кеширования."""
        default_ttl = 60
        raw_ttl = os.getenv("CACHE_TTL_MINUTES")
        ttl_value = default_ttl
        if raw_ttl is not None and raw_ttl.strip():
            try:
                parsed_ttl = int(raw_ttl)
                if parsed_ttl <= 0:
                    raise ValueError("Время жизни кеша должно быть положительным")
            except (ValueError, TypeError) as e:
                self.logger.warning(
                    "Некорректное значение CACHE_TTL_MINUTES='%s'. Использую %s. Ошибка: %s",
                    raw_ttl,
                    default_ttl,
                    e
                )
            else:
                ttl_value = parsed_ttl

        default_max_size = 1000
        raw_max_size = os.getenv("MAX_CACHE_SIZE")
        max_size_value = default_max_size
        if raw_max_size is not None and raw_max_size.strip():
            try:
                parsed_max_size = int(raw_max_size)
                if parsed_max_size <= 0:
                    raise ValueError("Максимальный размер кеша должен быть положительным")
            except (ValueError, TypeError) as e:
                self.logger.warning(
                    "Некорректное значение MAX_CACHE_SIZE='%s'. Использую %s. Ошибка: %s",
                    raw_max_size,
                    default_max_size,
                    e
                )
            else:
                max_size_value = parsed_max_size

        self.CACHE_TTL_MINUTES = ttl_value
        self.MAX_CACHE_SIZE = max_size_value

    def _emit_warnings(self) -> None:
        if self.DISCARDED_PAID_MODELS:
            self.logger.warning(
                "Платные модели были проигнорированы и не будут использоваться: %s.",
                ", ".join(self.DISCARDED_PAID_MODELS),
            )

        if "sqlite" in self.DATABASE_URL:
            self.logger.warning(
                "Используется локальная база данных SQLite для разработки. Для продакшена "
                "укажите DATABASE_URL."
            )

        if not self.OPENROUTER_API_KEY:
            self.logger.warning(
                "OPENROUTER_API_KEY не найден. Функция 'Бесплатный ChatGPT' будет недоступна."
            )

        # Новые предупреждения о валидации
        if self.WEBHOOK_URL and not self._validate_url(self.WEBHOOK_URL):
            self.logger.warning(
                "Некорректный WEBHOOK_URL в конфигурации: %s", self.WEBHOOK_URL
            )
            
        # Предупреждения о настройках кеширования
        if self.CACHE_TTL_MINUTES < 1:
            self.logger.warning("CACHE_TTL_MINUTES должен быть положительным числом, установлено значение по умолчанию: 60")
        if self.MAX_CACHE_SIZE < 1:
            self.logger.warning("MAX_CACHE_SIZE должен быть положительным числом, установлено значение по умолчанию: 1000")

    @staticmethod
    def _validate_database_url(url: str) -> bool:
        """Валидация URL базы данных."""
        valid_schemes = ('sqlite', 'postgresql', 'mysql', 'oracle')
        if '://' not in url:
            return False
        
        scheme = url.split('://', 1)[0]
        return scheme in valid_schemes

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _configure_logging(self) -> logging.Logger:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handlers: List[logging.Handler] = []

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        handlers.append(stream_handler)

        if self.LOG_TO_FILE:
            # Проверяем, что путь к файлу лога не содержит потенциально опасные символы
            if '..' in self.LOG_FILE_PATH or self.LOG_FILE_PATH.startswith('/'):
                raise ValueError("Некорректный путь к файлу лога")
            try:
                file_handler = logging.FileHandler(self.LOG_FILE_PATH, encoding="utf-8")
            except OSError as exc:  # pragma: no cover - зависимость от окружения
                raise ValueError(
                    f"Не удалось открыть файл лога '{self.LOG_FILE_PATH}': {exc}"
                ) from exc
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.handlers.clear()
        for handler in handlers:
            root_logger.addHandler(handler)

        configured_logger = logging.getLogger("sferatc_bot")
        configured_logger.propagate = True
        return configured_logger

    @staticmethod
    def _env_flag(name: str, *, default: bool = False) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _read_optional(name: str) -> Optional[str]:
        value = os.getenv(name)
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @staticmethod
    def _normalize_webhook_url(raw_url: Optional[str]) -> Optional[str]:
        if raw_url is None:
            return None
        cleaned = raw_url.strip()
        if not cleaned:
            return None
        return cleaned.rstrip("/")

    @staticmethod
    def _sanitize_webhook_path(path: Optional[str]) -> str:
        if not path:
            return ""
        return path.strip().strip("/")

    def _resolve_webhook_path(self, token: str, override: Optional[str]) -> str:
        if override is not None:
            return self._sanitize_webhook_path(override)
        return token.split(":")[-1] if token else ""

    def _resolve_webhook_port(self) -> int:
        fallback_port = 8443
        candidates = [
            ("PORT", os.getenv("PORT")),
            ("WEBHOOK_PORT", os.getenv("WEBHOOK_PORT")),
        ]

        for name, raw_value in candidates:
            if raw_value is None or raw_value.strip() == "":
                continue
            try:
                port = int(raw_value)
            except ValueError as exc:
                raise ValueError(
                    f"Переменная окружения {name} должна быть целым числом, получено '{raw_value}'."
                ) from exc
            if port <= 0:
                raise ValueError(
                    f"Переменная окружения {name} должна быть положительным числом, получено '{raw_value}'."
                )
            return port

        return fallback_port

    def _ensure_free_models(
        self, models: List[Optional[str]]
    ) -> tuple[List[str], List[str]]:
        free_models: List[str] = []
        discarded: List[str] = []

        for raw_model in models:
            if raw_model is None:
                continue
            sanitized = raw_model.strip()
            if not sanitized:
                continue
            normalized = sanitized.lower()
            if normalized.endswith(":free"):
                free_models.append(sanitized)
            else:
                discarded.append(sanitized)

        if not free_models:
            self.logger.warning(
                "Не найдены бесплатные модели в конфигурации. Будут использованы значения по умолчанию: %s.",
                ", ".join(self.DEFAULT_CHATGPT_FREE_MODELS),
            )
            free_models = self.DEFAULT_CHATGPT_FREE_MODELS.copy()

        return free_models, discarded


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Возвращает кэшированный экземпляр настроек."""

    return Settings()


def get_safe_url(url: Optional[str], context_name: str) -> Optional[str]:
    """Возвращает URL, если он задан, иначе логирует предупреждение."""

    if url:
        return url

    settings = get_settings()
    settings.logger.warning(
        "Отсутствует URL для '%s'. Будет использован текстовый fallback.",
        context_name,
    )
    return None
