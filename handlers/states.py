from enum import Enum, auto


class UserState(Enum):
    """Перечень состояний конечного автомата пользователя."""

    DEFAULT = auto()

    CHATGPT_ACTIVE = auto()
    CHATGPT_STREAMING = auto()

    SUPPORT_LLM_ACTIVE = auto()
    AWAITING_SUPPORT_MESSAGE = auto()

    AWAITING_VERIFICATION_ID = auto()


class AdminState(Enum):
    """Перечень состояний конечного автомата администратора."""

    DEFAULT = auto()
    BROADCAST_AWAITING_MESSAGE = auto()
    BROADCAST_AWAITING_CONFIRMATION = auto()
    BROADCAST_SCHEDULE_AWAITING_DATE = auto()  # Ожидание выбора даты
    BROADCAST_SCHEDULE_AWAITING_TIME = auto()  # Ожидание ввода времени
    BROADCAST_SCHEDULE_CONFIRMATION = auto()   # Подтверждение даты/времени
    BROADCAST_MANAGE_SCHEDULED = auto()        # Управление запланированными рассылками
    USERS_AWAITING_ID = auto()
    USERS_AWAITING_DM = auto()
