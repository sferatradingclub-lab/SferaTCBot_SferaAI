from enum import Enum, auto


class UserState(Enum):
    """Перечень состояний конечного автомата пользователя."""

    DEFAULT = auto()
    SUPPORT_LLM_ACTIVE = auto()
    AWAITING_SUPPORT_MESSAGE = auto()


class AdminState(Enum):
    """Перечень состояний конечного автомата администратора."""

    DEFAULT = auto()
    BROADCAST_AWAITING_MESSAGE = auto()
    BROADCAST_AWAITING_CONFIRMATION = auto()
    BROADCAST_SCHEDULE_AWAITING_DATE = auto()  # Ожидание выбора даты
    BROADCAST_SCHEDULE_AWAITING_TIME = auto()  # Ожидание ввода времени
    BROADCAST_SCHEDULE_CONFIRMATION = auto()   # Подтверждение даты/времени
    BROADCAST_MANAGE_SCHEDULED = auto()        # Управление запланированными рассылками
    BROADCAST_EDIT_AWAITING_TEXT = auto()      # Ожидание нового текста для редактирования рассылки
    BROADCAST_EDIT_AWAITING_DATE = auto()      # Ожидание выбора новой даты для рассылки
    BROADCAST_EDIT_AWAITING_TIME = auto()      # Ожидание ввода нового времени для рассылки
    BROADCAST_EDIT_AWAITING_MEDIA = auto()     # Ожидание нового медиа для редактирования рассылки
    BROADCAST_EDIT_AWAITING_BUTTONS = auto()   # Ожидание новых кнопок для редактирования рассылки
    USERS_AWAITING_ID = auto()
    USERS_AWAITING_DM = auto()
