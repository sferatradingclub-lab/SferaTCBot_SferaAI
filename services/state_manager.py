"""Helpers for managing FSM states stored in PTB context."""


from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Generic, Type, TypeVar

from telegram.ext import ContextTypes

from handlers.states import AdminState, UserState

_StateEnum = TypeVar("_StateEnum", bound=Enum)


@dataclass
class _StateDescriptor(Generic[_StateEnum]):
    key: str
    enum_cls: Type[_StateEnum]
    default: _StateEnum
    legacy_map: Dict[str, _StateEnum]


class StateManager:
    """Helper that encapsulates access to user state stored in context.user_data."""

    _USER_DESCRIPTOR = _StateDescriptor[UserState](
        key="state",
        enum_cls=UserState,
        default=UserState.DEFAULT,
        legacy_map={
            "support_llm_active": UserState.SUPPORT_LLM_ACTIVE,
            "awaiting_support_message": UserState.AWAITING_SUPPORT_MESSAGE,
        },
    )
    _ADMIN_DESCRIPTOR = _StateDescriptor[AdminState](
        key="admin_state",
        enum_cls=AdminState,
        default=AdminState.DEFAULT,
        legacy_map={
            "broadcast_awaiting_message": AdminState.BROADCAST_AWAITING_MESSAGE,
            "broadcast_awaiting_confirmation": AdminState.BROADCAST_AWAITING_CONFIRMATION,
            "users_awaiting_id": AdminState.USERS_AWAITING_ID,
            "users_awaiting_dm": AdminState.USERS_AWAITING_DM,
        },
    )

    def __init__(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        self._context = context

    def get_user_state(self) -> UserState:
        return self._get_state(self._USER_DESCRIPTOR)

    def set_user_state(self, state: UserState) -> None:
        self._set_state(self._USER_DESCRIPTOR, state)

    def reset_user_state(self) -> None:
        self.set_user_state(UserState.DEFAULT)

    def get_admin_state(self) -> AdminState:
        return self._get_state(self._ADMIN_DESCRIPTOR)

    def set_admin_state(self, state: AdminState) -> None:
        self._set_state(self._ADMIN_DESCRIPTOR, state)

    def reset_admin_state(self) -> None:
        self.set_admin_state(AdminState.DEFAULT)

    def clear_user_data_key(self, key: str) -> None:
        self._context.user_data.pop(key, None)

    def _get_state(self, descriptor: _StateDescriptor[_StateEnum]) -> _StateEnum:
        raw_state: Any = self._context.user_data.get(descriptor.key, descriptor.default)
        if isinstance(raw_state, descriptor.enum_cls):
            return raw_state
        if isinstance(raw_state, str):
            mapped = descriptor.legacy_map.get(raw_state)
            if mapped is not None:
                return mapped
        try:
            return descriptor.enum_cls(raw_state)  # type: ignore[arg-type]
        except Exception:
            return descriptor.default

    def _set_state(self, descriptor: _StateDescriptor[_StateEnum], state: _StateEnum) -> None:
        self._context.user_data[descriptor.key] = state


__all__ = ["StateManager"]
