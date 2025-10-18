import pytest
from unittest.mock import MagicMock

from handlers.states import AdminState, UserState
from services.state_manager import StateManager


class TestStateManager:
    """Тесты для StateManager - управление состояниями пользователей и администраторов."""

    def test_get_user_state_default(self):
        """Тест получения пользовательского состояния по умолчанию."""
        context = MagicMock()
        context.user_data = {}
        
        state_manager = StateManager(context)
        state = state_manager.get_user_state()
        
        assert state == UserState.DEFAULT

    def test_set_and_get_user_state(self):
        """Тест установки и получения пользовательского состояния."""
        context = MagicMock()
        context.user_data = {}
        
        state_manager = StateManager(context)
        state_manager.set_user_state(UserState.CHATGPT_ACTIVE)
        
        assert state_manager.get_user_state() == UserState.CHATGPT_ACTIVE
        assert context.user_data["state"] == UserState.CHATGPT_ACTIVE

    def test_get_admin_state_default(self):
        """Тест получения административного состояния по умолчанию."""
        context = MagicMock()
        context.user_data = {}
        
        state_manager = StateManager(context)
        state = state_manager.get_admin_state()
        
        assert state == AdminState.DEFAULT

    def test_set_and_get_admin_state(self):
        """Тест установки и получения административного состояния."""
        context = MagicMock()
        context.user_data = {}
        
        state_manager = StateManager(context)
        state_manager.set_admin_state(AdminState.BROADCAST_AWAITING_MESSAGE)
        
        assert state_manager.get_admin_state() == AdminState.BROADCAST_AWAITING_MESSAGE
        assert context.user_data["admin_state"] == AdminState.BROADCAST_AWAITING_MESSAGE

    def test_reset_user_state(self):
        """Тест сброса пользовательского состояния."""
        context = MagicMock()
        context.user_data = {"state": UserState.CHATGPT_ACTIVE}
        
        state_manager = StateManager(context)
        state_manager.reset_user_state()
        
        assert state_manager.get_user_state() == UserState.DEFAULT
        assert context.user_data["state"] == UserState.DEFAULT

    def test_reset_admin_state(self):
        """Тест сброса административного состояния."""
        context = MagicMock()
        context.user_data = {"admin_state": AdminState.BROADCAST_AWAITING_CONFIRMATION}
        
        state_manager = StateManager(context)
        state_manager.reset_admin_state()
        
        assert state_manager.get_admin_state() == AdminState.DEFAULT
        assert context.user_data["admin_state"] == AdminState.DEFAULT

    def test_clear_user_data_key(self):
        """Тест очистки ключа из пользовательских данных."""
        context = MagicMock()
        context.user_data = {"state": UserState.CHATGPT_ACTIVE, "other_key": "value"}
        
        state_manager = StateManager(context)
        state_manager.clear_user_data_key("other_key")
        
        assert "other_key" not in context.user_data
        assert context.user_data["state"] == UserState.CHATGPT_ACTIVE

    def test_clear_nonexistent_user_data_key(self):
        """Тест очистки несуществующего ключа из пользовательских данных."""
        context = MagicMock()
        context.user_data = {"state": UserState.CHATGPT_ACTIVE}
        
        state_manager = StateManager(context)
        # Не должно вызывать исключений
        state_manager.clear_user_data_key("nonexistent_key")
        
        assert context.user_data["state"] == UserState.CHATGPT_ACTIVE

    def test_legacy_user_state_mapping(self):
        """Тест сопоставления устаревших состояний пользователя."""
        context = MagicMock()
        context.user_data = {"state": "chatgpt_active"}  # Legacy string format
        
        state_manager = StateManager(context)
        state = state_manager.get_user_state()
        
        assert state == UserState.CHATGPT_ACTIVE

    def test_legacy_admin_state_mapping(self):
        """Тест сопоставления устаревших состояний администратора."""
        context = MagicMock()
        context.user_data = {"admin_state": "broadcast_awaiting_message"}  # Legacy string format
        
        state_manager = StateManager(context)
        state = state_manager.get_admin_state()
        
        assert state == AdminState.BROADCAST_AWAITING_MESSAGE

    def test_invalid_state_fallback_to_default(self):
        """Тест fallback к состоянию по умолчанию при некорректном значении."""
        context = MagicMock()
        context.user_data = {"state": "invalid_state"}
        
        state_manager = StateManager(context)
        state = state_manager.get_user_state()
        
        assert state == UserState.DEFAULT

    def test_integer_state_conversion(self):
        """Тест преобразования целочисленного состояния."""
        context = MagicMock()
        context.user_data = {"state": 1}  # Integer state
        
        state_manager = StateManager(context)
        state = state_manager.get_user_state()
        
        # Должен успешно преобразовать в enum значение
        assert isinstance(state, UserState)

    def test_none_state_fallback_to_default(self):
        """Тест fallback к состоянию по умолчанию при None значении."""
        context = MagicMock()
        context.user_data = {"state": None}
        
        state_manager = StateManager(context)
        state = state_manager.get_user_state()
        
        assert state == UserState.DEFAULT

    def test_all_user_states_persistence(self):
        """Тест сохранения всех пользовательских состояний."""
        context = MagicMock()
        context.user_data = {}
        
        state_manager = StateManager(context)
        
        user_states = [
            UserState.DEFAULT,
            UserState.CHATGPT_ACTIVE,
            UserState.CHATGPT_STREAMING,
            UserState.SUPPORT_LLM_ACTIVE,
            UserState.AWAITING_SUPPORT_MESSAGE,
            UserState.AWAITING_VERIFICATION_ID,
        ]
        
        for state in user_states:
            state_manager.set_user_state(state)
            assert state_manager.get_user_state() == state

    def test_all_admin_states_persistence(self):
        """Тест сохранения всех административных состояний."""
        context = MagicMock()
        context.user_data = {}
        
        state_manager = StateManager(context)
        
        admin_states = [
            AdminState.DEFAULT,
            AdminState.BROADCAST_AWAITING_MESSAGE,
            AdminState.BROADCAST_AWAITING_CONFIRMATION,
            AdminState.USERS_AWAITING_ID,
            AdminState.USERS_AWAITING_DM,
        ]
        
        for state in admin_states:
            state_manager.set_admin_state(state)
            assert state_manager.get_admin_state() == state

    def test_multiple_state_managers_independence(self):
        """Тест независимости нескольких менеджеров состояний."""
        context1 = MagicMock()
        context1.user_data = {}
        
        context2 = MagicMock()
        context2.user_data = {}
        
        state_manager1 = StateManager(context1)
        state_manager2 = StateManager(context2)
        
        state_manager1.set_user_state(UserState.CHATGPT_ACTIVE)
        state_manager2.set_user_state(UserState.SUPPORT_LLM_ACTIVE)
        
        assert state_manager1.get_user_state() == UserState.CHATGPT_ACTIVE
        assert state_manager2.get_user_state() == UserState.SUPPORT_LLM_ACTIVE
        assert context1.user_data["state"] == UserState.CHATGPT_ACTIVE
        assert context2.user_data["state"] == UserState.SUPPORT_LLM_ACTIVE

    def test_state_descriptor_constants(self):
        """Тест корректности констант дескрипторов состояний."""
        from services.state_manager import StateManager
        
        # Проверяем что дескрипторы имеют правильные ключи
        assert StateManager._USER_DESCRIPTOR.key == "state"
        assert StateManager._USER_DESCRIPTOR.enum_cls == UserState
        assert StateManager._USER_DESCRIPTOR.default == UserState.DEFAULT
        
        assert StateManager._ADMIN_DESCRIPTOR.key == "admin_state"
        assert StateManager._ADMIN_DESCRIPTOR.enum_cls == AdminState
        assert StateManager._ADMIN_DESCRIPTOR.default == AdminState.DEFAULT

    def test_legacy_map_completeness(self):
        """Тест полноты legacy mapping для всех состояний."""
        from services.state_manager import StateManager
        
        # Проверяем что все legacy ключи сопоставлены
        expected_user_legacy = {
            "chatgpt_active": UserState.CHATGPT_ACTIVE,
            "support_llm_active": UserState.SUPPORT_LLM_ACTIVE,
            "awaiting_support_message": UserState.AWAITING_SUPPORT_MESSAGE,
        }
        
        expected_admin_legacy = {
            "broadcast_awaiting_message": AdminState.BROADCAST_AWAITING_MESSAGE,
            "broadcast_awaiting_confirmation": AdminState.BROADCAST_AWAITING_CONFIRMATION,
            "users_awaiting_id": AdminState.USERS_AWAITING_ID,
            "users_awaiting_dm": AdminState.USERS_AWAITING_DM,
        }
        
        assert StateManager._USER_DESCRIPTOR.legacy_map == expected_user_legacy
        assert StateManager._ADMIN_DESCRIPTOR.legacy_map == expected_admin_legacy