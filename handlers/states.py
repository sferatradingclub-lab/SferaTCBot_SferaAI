from enum import Enum, auto


class UserState(Enum):
    """Перечень состояний конечного автомата пользователя."""

    DEFAULT = auto()

    CHATGPT_ACTIVE = auto()

    SUPPORT_LLM_ACTIVE = auto()
    AWAITING_SUPPORT_MESSAGE = auto()

    AWAITING_VERIFICATION_ID = auto()


class AdminState(Enum):
    """Перечень состояний конечного автомата администратора."""

    DEFAULT = auto()
    BROADCAST_AWAITING_MESSAGE = auto()
    BROADCAST_AWAITING_CONFIRMATION = auto()
    USERS_AWAITING_ID = auto()
    USERS_AWAITING_DM = auto()
