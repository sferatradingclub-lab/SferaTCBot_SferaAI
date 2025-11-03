# Итоговый план реализации функции отложенной рассылки

## 1. Внесенные изменения

### 1.1. Исправлена синтаксическая ошибка в `models/base.py`
- Удалена лишняя буква "t" в начале строки: `tfrom sqlalchemy import create_engine` → `from sqlalchemy import create_engine`

### 1.2. Создана модель `ScheduledBroadcast` в `models/broadcast.py`
```python
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from .base import Base

class ScheduledBroadcast(Base):
    __tablename__ = "scheduled_broadcasts"
    
    id = Column(Integer, primary_key=True, index=True)
    message_content = Column(Text, nullable=False)  # JSON-строка с содержимым сообщения
    scheduled_datetime = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    admin_id = Column(Integer, nullable=False)  # ID администратора, создавшего рассылку
```

### 1.3. Добавлены CRUD-операции в `models/crud.py`
- `create_scheduled_broadcast(db, admin_id, message_content, scheduled_datetime)`
- `get_scheduled_broadcast(db, broadcast_id)`
- `get_scheduled_broadcasts_by_admin(db, admin_id)`
- `get_pending_scheduled_broadcasts(db)`
- `update_scheduled_broadcast(db, broadcast_id, **kwargs)`
- `mark_broadcast_as_sent(db, broadcast_id)`
- `delete_scheduled_broadcast(db, broadcast_id)`

### 1.4. Реализована инлайн-клавиатура календаря в `handlers/calendar.py`
- Функция `create_calendar_keyboard(target_date=None)` создает клавиатуру с календарем
- Функция `create_date_quick_select_keyboard()` создает кнопки быстрого выбора даты
- Календарь включает навигацию по месяцам и выбор даты

### 1.5. Добавлены новые состояния в `handlers/states.py`
```python
class AdminState(Enum):
    # ... существующие состояния ...
    BROADCAST_SCHEDULE_AWAITING_DATE = auto()  # Ожидание выбора даты
    BROADCAST_SCHEDULE_AWAITING_TIME = auto()  # Ожидание ввода времени
    BROADCAST_SCHEDULE_CONFIRMATION = auto()   # Подтверждение даты/времени
    BROADCAST_MANAGE_SCHEDULED = auto()        # Управление запланированными рассылками
```

### 1.6. Добавлена логика обработки отложенной рассылки в `handlers/admin/broadcast.py`
- Функция `handle_calendar_callback` для обработки callback-запросов от календаря
- Функция `handle_scheduled_broadcast_time_input` для обработки ввода времени
- Функция `handle_scheduled_broadcast_confirmation` для подтверждения параметров рассылки
- Функция `handle_scheduled_broadcasts_list` для отображения запланированных рассылок

### 1.7. Обновлены обработчики в `handlers/admin_handlers.py`
- Обновлена функция `admin_menu_handler` для обработки календарных команд
- Добавлены проверки состояний и логирование

### 1.8. Добавлен планировщик рассылок в `services/broadcast_scheduler.py`
- Сервис `BroadcastSchedulerService` для проверки и отправки запланированных рассылок
- Задача выполняется каждую минуту для проверки необходимости отправки

### 1.9. Обновлен `main.py` для регистрации новых обработчиков
- Добавлен обработчик для календарных команд: `application.add_handler(CallbackQueryHandler(admin_menu_handler, pattern='^calendar_'))`
- Добавлена задача для проверки и отправки запланированных рассылок

## 2. Логика работы

### 2.1. Сценарий отложенной рассылки
1. Администратор отправляет сообщение для рассылки
2. Бот показывает предварительный просмотр сообщения
3. Вместо двух кнопок ("отправить всем", "отмена") появляется три:
   - "Да, отправить сейчас"
   - "Отложенная отправка"
   - "Отмена"
4. При выборе "Отложенная отправка":
   - Бот показывает кнопки: "Развернуть календарь", "Сегодня", "Завтра", "Послезавтра"
   - При нажатии на "Развернуть календарь" - отображается календарь с навигацией по месяцам
   - При выборе даты - бот запрашивает время в формате ЧЧ:ММ
   - При вводе времени - бот подтверждает дату и время отправки
   - После подтверждения - рассылка сохраняется в базе данных
   - В заданное время - рассылка отправляется

### 2.2. Управление запланированными рассылками
- Отображение списка запланированных рассылок с кнопками "Все запланированные рассылки"
- Возможность просмотра деталей каждой рассылки
- Возможность изменения даты/времени или отмены рассылки

## 3. Особенности реализации

### 3.1. Хранение содержимого сообщения
Содержимое сообщения сериализуется в JSON формат и сохраняется в поле `message_content` модели `ScheduledBroadcast`. Это позволяет воссоздать оригинальное сообщение при отправке, включая текст, изображения и другие медиа.

### 3.2. Обработка ошибок
- Проверка корректности формата времени
- Проверка, что дата не в прошлом
- Обработка ошибок при отправке рассылки
- Обработка ошибок при работе с базой данных

### 3.3. Безопасность
- Проверка прав администратора при доступе к функциям рассылки
- Защита от спама через ограничение количества запланированных рассылок
- Логирование всех действий по рассылке

## 4. Тестирование

Функционал должен быть протестирован на:
- Корректность выбора даты и времени
- Правильную работу календаря (навигация по месяцам, выбор даты)
- Сохранение и восстановление содержимого сообщения
- Отправку рассылок в заданное время
- Обработку ошибок
- Права доступа администратора