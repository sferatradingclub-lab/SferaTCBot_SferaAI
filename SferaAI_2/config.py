"""
Конфигурационный файл для Sfera AI Agent
Содержит все настройки, параметры и константы для работы агента
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


@dataclass
class AgentConfig:
    """Конфигурация AI агента"""
    model_name: str = "gemini-live-2.5-flash-preview"
    voice: str = "Aoede"
    temperature: float = 0.0
    thinking_budget: int = 0
    silence_duration_ms: int = 800
    max_memories_to_load: int = 100


@dataclass
class MemoryConfig:
    """Конфигурация системы памяти"""
    user_name: str = "David"
    max_memories_per_user: int = 1000
    memory_retention_days: int = 365
    enable_semantic_search: bool = True
    similarity_threshold: float = 0.7


@dataclass
class LiveKitConfig:
    """Конфигурация LiveKit"""
    url: str = ""
    api_key: str = ""
    api_secret: str = ""
    video_enabled: bool = True
    noise_cancellation_enabled: bool = True


@dataclass
class LoggingConfig:
    """Конфигурация логирования"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_file_logging: bool = False
    log_file_path: str = "logs/agent.log"


@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    collection_name: str = "sfera_ai_memory"
    kb_collection_name: str = "global_knowledge_base"
    dense_vector_name: str = "dense_kb"
    sparse_vector_name: str = "sparse_kb"
    vector_size: int = 384
    distance_metric: str = "COSINE"


@dataclass
class APIEndpoints:
    """API endpoints для внешних сервисов"""
    binance_base: str = "https://api.binance.com/api/v3"
    binance_price: str = "https://api.binance.com/api/v3/ticker/price"
    weather_api: str = "https://wttr.in"
    google_cse_base: str = "https://www.googleapis.com/customsearch/v1"


@dataclass
class CacheSettings:
    """Настройки кэширования"""
    web_search_ttl: int = 600       # 10 минут
    kb_search_ttl: int = 1800        # 30 минут
    crypto_price_ttl: int = 30       # 30 секунд
    video_search_ttl: int = 3600     # 1 час
    
    web_search_max_size: int = 50
    kb_max_size: int = 100
    crypto_max_size: int = 100


@dataclass
class SearchSettings:
    """Настройки поиска"""
    google_timeout: int = 8
    binance_timeout: int = 5
    weather_timeout: int = 5
    max_search_results: int = 5
    video_search_results: int = 3
    safesearch: str = "off"


@dataclass
class KnowledgeBaseSettings:
    """Настройки базы знаний"""
    dense_weight: float = 0.6
    sparse_weight: float = 0.4
    chunk_size: int = 1500
    chunk_overlap: int = 200
    similarity_threshold: float = 0.7
    max_results: int = 5
    qdrant_timeout: int = 30


@dataclass
class PromptSettings:
    """Настройки промптов"""
    modules_dir: str = "prompts/system"
    personas_dir: str = "prompts/personas"
    enable_versioning: bool = True
    default_persona: str = "partner"


class Config:
    """Главный класс конфигурации"""
    
    def __init__(self):
        self.agent = AgentConfig()
        self.memory = MemoryConfig()
        self.livekit = LiveKitConfig()
        self.logging = LoggingConfig()
        self.database = DatabaseConfig()
        self.api = APIEndpoints()
        self.cache = CacheSettings()
        self.search = SearchSettings()
        self.kb = KnowledgeBaseSettings()
        self.prompts = PromptSettings()
        
        self._load_from_env()
    
    def _load_from_env(self):
        """Загрузка настроек из переменных окружения"""
        self.livekit.url = os.getenv("LIVEKIT_URL", "")
        self.livekit.api_key = os.getenv("LIVEKIT_API_KEY", "")
        self.livekit.api_secret = os.getenv("LIVEKIT_API_SECRET", "")
        
        self.memory.user_name = os.getenv("AGENT_USER_NAME", self.memory.user_name)
        
        log_level = os.getenv("LOG_LEVEL")
        if log_level:
            self.logging.level = log_level.upper()
        
        model_name = os.getenv("GEMINI_MODEL_NAME")
        if model_name:
            self.agent.model_name = model_name
    
    def validate(self) -> Dict[str, Any]:
        """Валидация конфигурации"""
        errors = []
        warnings = []
        
        if not self.livekit.url:
            errors.append("LIVEKIT_URL не установлен")
        if not self.livekit.api_key:
            errors.append("LIVEKIT_API_KEY не установлен")
        if not self.livekit.api_secret:
            errors.append("LIVEKIT_API_SECRET не установлен")
        
        qdrant_host = os.getenv("QDRANT_HOST")
        qdrant_key = os.getenv("QDRANT_API_KEY")
        if not qdrant_host:
            errors.append("QDRANT_HOST не установлен")
        if not qdrant_key:
            errors.append("QDRANT_API_KEY не установлен")
            
        google_key = os.getenv("GOOGLE_API_KEY")
        if not google_key:
            warnings.append("GOOGLE_API_KEY не установлен")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def get_thinking_config(self):
        """Получение конфигурации размышлений для Gemini"""
        from google.genai import types
        return types.ThinkingConfig(
            thinking_budget=self.agent.thinking_budget
        )
    
    def get_realtime_input_config(self):
        """Получение конфигурации ввода для Realtime модели"""
        from google.genai import types
        return types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                silence_duration_ms=self.agent.silence_duration_ms,
            )
        )


config = Config()

GREETINGS = {
    "russian": "Привет, я Sfera AI. Твоя ассистентка и напарница. Чем сегодня займемся?",
    "english": "Hello! I'm Sfera AI, your personal assistant and partner. What shall we work on today?",
    "greeting_prompt": "Greet me as Sfera AI assistant"
}

SECURITY = {
    "max_memory_size_mb": 100,
    "max_conversation_length": 1000,
    "enable_content_filtering": True,
    "allowed_languages": ["ru", "en"],
    "session_timeout_minutes": 60
}

PERFORMANCE = {
    "max_concurrent_sessions": int(os.getenv("MAX_CONCURRENT_SESSIONS", "1000")),
    "memory_cleanup_interval_hours": 24,
    "vector_search_limit": 10,
    "response_timeout_seconds": 30,
    "enable_caching": True
}

if __name__ == "__main__":
    validation = config.validate()
    print("Конфигурация валидна:", validation["valid"])
    
    if validation["errors"]:
        print("Ошибки:", validation["errors"])
    
    if validation["warnings"]:
        print("Предупреждения:", validation["warnings"])
    
    print(f"Пользователь: {config.memory.user_name}")
    print(f"Модель: {config.agent.model_name}")
    print(f"Голос: {config.agent.voice}")