# Руководство разработчика

## Структура проекта

### Организация кода

Проект следует модульной архитектуре с четким разделением ответственности:

```
sferatc-bot/
├── handlers/           # Обработчики команд и сообщений
├── services/           # Бизнес-логика и сервисы
├── models/             # Модели базы данных
├── tests/              # Тесты
├── docs/               # Документация
└── scripts/            # Вспомогательные скрипты
```

### Соглашения об именовании

- **Файлы:** `snake_case.py`
- **Классы:** `PascalCase`
- **Функции/методы:** `snake_case`
- **Константы:** `SCREAMING_SNAKE_CASE`
- **Переменные:** `snake_case`

## Разработка новых функций

### 1. Создание обработчика команд

```python
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from services.state_manager import StateManager
from handlers.decorators import user_required

@user_required
async def my_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Описание команды для пользователей."""
    
    state_manager = StateManager(context)
    user = update.effective_user
    
    await update.message.reply_text(
        f"Привет, {user.first_name}! Это новая команда."
    )
    
    # Устанавливаем состояние если нужно
    # state_manager.set_user_state(UserState.MY_NEW_STATE)

# Регистрация в main.py
application.add_handler(CommandHandler("mycommand", my_command))
```

### 2. Создание сервиса

```python
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User

class MyService:
    """Новый сервис для бизнес-логики."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def get_data(self, user_id: int) -> Optional[dict]:
        """Получить данные для пользователя."""
        # Реализация логики
        pass
    
    async def process_data(self, data: dict) -> bool:
        """Обработать данные."""
        # Реализация логики
        pass
```

### 3. Создание модели базы данных

```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from models.base import Base

class MyModel(Base):
    __tablename__ = "my_table"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Связи
    user = relationship("User", back_populates="my_models")
```

## Работа состояниями

### Определение новых состояний

```python
from enum import Enum, auto

class UserState(Enum):
    """Состояния пользователя."""
    
    DEFAULT = auto()
    MY_NEW_STATE = auto()
    AWAITING_INPUT = auto()
```

### Использование состояний в обработчиках

```python
from handlers.states import UserState
from services.state_manager import StateManager

async def enter_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state_manager = StateManager(context)
    state_manager.set_user_state(UserState.MY_NEW_STATE)
    
    await update.message.reply_text("Теперь вы в новом состоянии")

async def handle_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state_manager = StateManager(context)
    
    if state_manager.get_user_state() == UserState.MY_NEW_STATE:
        # Обработка в этом состоянии
        await update.message.reply_text("Обработка в MY_NEW_STATE")
        
        # Выход из состояния
        state_manager.reset_user_state()
```

## Работа с базой данных

### CRUD операции

```python
from models.crud import CRUDAbstractBase
from models.my_model import MyModel

class CRUDMyModel(CRUDAbstractBase):
    async def get_by_user_id(self, db: AsyncSession, user_id: int) -> List[MyModel]:
        result = await db.execute(
            select(MyModel).where(MyModel.user_id == user_id)
        )
        return result.scalars().all()
    
    async def create_with_user(
        self, 
        db: AsyncSession, 
        obj_in: dict, 
        user_id: int
    ) -> MyModel:
        obj_in["user_id"] = user_id
        return await self.create(db, obj_in=obj_in)

crud_my_model = CRUDMyModel(MyModel)
```

### Использование в сервисах

```python
class MyService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.crud = crud_my_model
    
    async def get_user_data(self, user_id: int) -> List[dict]:
        models = await self.crud.get_by_user_id(self.db_session, user_id)
        return [model.__dict__ for model in models]
```

## Тестирование

### Структура тестов

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

class TestMyFeature:
    """Тесты для новой функции."""
    
    async def test_my_command(self, async_client: AsyncClient):
        """Тест команды."""
        response = await async_client.post("/my_endpoint")
        assert response.status_code == 200
    
    async def test_my_service(self, db_session: AsyncSession):
        """Тест сервиса."""
        service = MyService(db_session)
        result = await service.get_data(123)
        assert result is not None
    
    async def test_my_model(self, db_session: AsyncSession):
        """Тест модели."""
        # Создание тестовых данных
        model = MyModel(name="test", user_id=123)
        db_session.add(model)
        await db_session.commit()
        
        # Проверка
        result = await db_session.get(MyModel, model.id)
        assert result.name == "test"
```

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=. --cov-report=html

# Конкретный файл
pytest tests/test_my_feature.py -v

# Только неудачные тесты
pytest --lf

# Параллельное выполнение
pytest -n auto
```

## Логирование

### Стандарты логирования

```python
import logging
from config import get_settings

settings = get_settings()
logger = settings.logger

class MyService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def process(self):
        self.logger.info("Начало обработки")
        
        try:
            # Логика
            self.logger.debug("Детальная информация")
        except Exception as e:
            self.logger.error(f"Ошибка обработки: {e}", exc_info=True)
        finally:
            self.logger.info("Обработка завершена")
```

### Уровни логирования

- **DEBUG:** Детальная информация для отладки
- **INFO:** Общая информация о работе приложения
- **WARNING:** Предупреждения о потенциальных проблемах
- **ERROR:** Ошибки, которые не останавливают приложение
- **CRITICAL:** Критические ошибки, требующие немедленного внимания

## Обработка ошибок

### Глобальная обработка ошибок

```python
from services.enhanced_error_handler import EnhancedErrorHandler

async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Логика обработчика
        pass
    except Exception as e:
        error_handler = EnhancedErrorHandler(context.bot)
        await error_handler.handle_error(e, update)
        raise
```

### Кастомные исключения

```python
class MyCustomError(Exception):
    """Кастомное исключение для бизнес-логики."""
    pass

class MyService:
    async def risky_operation(self):
        if some_condition:
            raise MyCustomError("Описание ошибки")
        
        # Продолжение логики
```

## Производительность

### Оптимизация запросов

```python
# Плохо: N+1 запросов
for user in users:
    posts = await get_posts_by_user(user.id)  # N запросов

# Хорошо: один запрос с JOIN
posts_by_users = await get_posts_with_users()  # 1 запрос
```

### Кеширование

```python
from services.cache_service import CacheService
from functools import lru_cache

class MyService:
    def __init__(self):
        self.cache = CacheService()
    
    @lru_cache(maxsize=128)
    async def get_expensive_data(self, param: str):
        # Проверка кеша
        cached = await self.cache.get(f"expensive_data:{param}")
        if cached:
            return cached
        
        # Вычисление данных
        result = await self._compute_expensive_data(param)
        
        # Сохранение в кеш
        await self.cache.set(f"expensive_data:{param}", result, ttl=3600)
        
        return result
```

## Документирование кода

### Docstrings

```python
def my_function(param1: str, param2: int) -> dict:
    """
    Подробное описание функции.
    
    Args:
        param1: Описание первого параметра
        param2: Описание второго параметра
    
    Returns:
        Описание возвращаемого значения
    
    Raises:
        ValueError: Когда параметр некорректен
        ConnectionError: При проблемах с сетью
    
    Example:
        >>> result = my_function("test", 42)
        {'status': 'success'}
    """
    pass
```

### Комментарии в коде

```python
# Плохо
if x > 0:  # проверка
    return True

# Хорошо
# Проверяем, что значение положительное для корректной работы алгоритма
if x > 0:
    return True
```

## Рабочий процесс разработки

### Git workflow

1. **Создание ветки:**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Разработка:**
   - Делайте небольшие коммиты
   - Пишите понятные сообщения коммитов
   - Добавляйте тесты для новых функций

3. **Тестирование:**
   ```bash
   pytest tests/test_new_feature.py
   ```

4. **Самопроверка:**
   ```bash
   # Форматирование кода
   black .
   # Линтинг
   flake8 .
   # Типизация
   mypy .
   ```

5. **Создание Pull Request:**
   - Опишите изменения
   - Укажите связанные issues
   - Запросите ревью коллег

### Code Review checklist

- [ ] Код соответствует стандартам проекта
- [ ] Добавлены тесты для новой функциональности
- [ ] Обновлена документация
- [ ] Нет очевидных ошибок безопасности
- [ ] Производительность не ухудшилась
- [ ] Логирование соответствует стандартам

## Интеграция с внешними сервисами

### Добавление нового API

```python
import httpx
from config import get_settings

class ExternalAPIService:
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient()
    
    async def call_external_api(self, data: dict) -> dict:
        """Вызов внешнего API."""
        response = await self.client.post(
            "https://api.example.com/endpoint",
            json=data,
            headers={"Authorization": f"Bearer {self.settings.API_TOKEN}"}
        )
        response.raise_for_status()
        return response.json()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
```

## Деплой

### Подготовка к деплою

1. **Обновление зависимостей:**
   ```bash
   pip freeze > requirements.txt
   ```

2. **Создание миграций:**
   ```bash
   # Если изменилась структура БД
   python migrate.py
   ```

3. **Тестирование:**
   ```bash
   pytest --cov=. --cov-report=html
   ```

### Docker деплой

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python migrate.py

EXPOSE 8443
CMD ["uvicorn", "main:asgi_app", "--host", "0.0.0.0", "--port", "8443"]
```

## Мониторинг и поддержка

### Метрики

Важные метрики для мониторинга:
- Время ответа бота
- Количество активных пользователей
- Частота ошибок
- Использование памяти и CPU

### Логи

Настройте централизованное логирование:
```python
import logging.handlers

# Отправка логов в внешнюю систему
handler = logging.handlers.SysLogHandler(address='/dev/log')
logger.addHandler(handler)
```

---

**Последнее обновление:** Октябрь 2025