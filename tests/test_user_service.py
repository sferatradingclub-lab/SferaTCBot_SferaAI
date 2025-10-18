import pytest
from unittest.mock import MagicMock, patch

from services.user_service import get_or_create_user
from models.user import User


class TestUserService:
    """Тесты для user_service - работа с пользователями."""

    @pytest.fixture
    def mock_update(self):
        """Фикстура для создания мок-обновления."""
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456
        update.effective_user.username = "testuser"
        update.effective_user.full_name = "Test User"
        return update

    @pytest.fixture
    def mock_context(self):
        """Фикстура для создания мок-контекста."""
        return MagicMock()

    @pytest.fixture
    def mock_db_session(self):
        """Фикстура для создания мок-сессии базы данных."""
        session = MagicMock()
        return session

    def test_get_or_create_user_new_user(self, mock_update, mock_context, mock_db_session):
        """Тест получения или создания нового пользователя."""
        # Имитируем отсутствие пользователя в базе
        with patch('services.user_service.get_user', return_value=None), \
             patch('services.user_service.create_user') as mock_create_user:
            
            # Создаем мок-пользователя для возврата
            mock_new_user = User(
                id=123456,
                username="testuser",
                full_name="Test User"
            )
            mock_create_user.return_value = mock_new_user
            
            with patch('services.user_service.get_db') as mock_get_db:
                mock_get_db.return_value.__enter__.return_value = mock_db_session
                
                user, created = get_or_create_user(mock_update, mock_context)
                
                # Проверяем, что пользователь был создан
                assert user == mock_new_user
                assert created is True
                mock_create_user.assert_called_once()

    def test_get_or_create_user_existing_user(self, mock_update, mock_context, mock_db_session):
        """Тест получения существующего пользователя."""
        # Имитируем существующего пользователя в базе
        mock_existing_user = User(
            id=123456,
            username="testuser",
            full_name="Test User"
        )
        
        with patch('services.user_service.get_user', return_value=mock_existing_user), \
             patch('services.user_service.create_user') as mock_create_user:
            
            with patch('services.user_service.get_db') as mock_get_db:
                mock_get_db.return_value.__enter__.return_value = mock_db_session
                
                user, created = get_or_create_user(mock_update, mock_context)
                
                # Проверяем, что пользователь был получен, а не создан
                assert user == mock_existing_user
                assert created is False
                mock_create_user.assert_not_called()

    def test_get_or_create_user_no_effective_user(self, mock_context):
        """Тест получения пользователя при отсутствии effective_user."""
        update = MagicMock()
        update.effective_user = None
        
        user, created = get_or_create_user(update, mock_context)
        
        # Проверяем, что функция возвращает None
        assert user is None
        assert created is False

    def test_get_or_create_user_with_special_characters(self, mock_context, mock_db_session):
        """Тест получения или создания пользователя со специальными символами в имени."""
        # Создаем мок-обновление символами в имени
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456
        update.effective_user.username = "test_user_123"
        update.effective_user.full_name = "Test User с кириллицей и символами: @#$%^&*"
        
        # Имитируем отсутствие пользователя в базе
        with patch('services.user_service.get_user', return_value=None), \
             patch('services.user_service.create_user') as mock_create_user:
            
            # Создаем мок-пользователя для возврата
            mock_new_user = User(
                id=123456,
                username="test_user_123",
                full_name="Test User с кириллицей и символами: @#$%^&*"
            )
            mock_create_user.return_value = mock_new_user
            
            with patch('services.user_service.get_db') as mock_get_db:
                mock_get_db.return_value.__enter__.return_value = mock_db_session
                
                user, created = get_or_create_user(update, mock_context)
                
                # Проверяем, что пользователь был создан с правильными данными
                assert user == mock_new_user
                assert created is True
                mock_create_user.assert_called_once()

    def test_get_or_create_user_with_none_username(self, mock_context, mock_db_session):
        """Тест получения или создания пользователя с None в username."""
        # Создаем мок-обновление с None в username
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 123456
        update.effective_user.username = None
        update.effective_user.full_name = "Test User"
        
        # Имитируем отсутствие пользователя в базе
        with patch('services.user_service.get_user', return_value=None), \
             patch('services.user_service.create_user') as mock_create_user:
            
            # Создаем мок-пользователя для возврата
            mock_new_user = User(
                id=123456,
                username=None,
                full_name="Test User"
            )
            mock_create_user.return_value = mock_new_user
            
            with patch('services.user_service.get_db') as mock_get_db:
                mock_get_db.return_value.__enter__.return_value = mock_db_session
                
                user, created = get_or_create_user(update, mock_context)
                
                # Проверяем, что пользователь был создан с правильными данными
                assert user == mock_new_user
                assert created is True
                mock_create_user.assert_called_once()

    def test_get_or_create_user_database_error(self, mock_update, mock_context, mock_db_session):
        """Тест обработки ошибки базы данных."""
        # Имитируем ошибку при работе с базой данных
        with patch('services.user_service.get_user', side_effect=Exception("DB Error")):
            
            with patch('services.user_service.get_db') as mock_get_db:
                mock_get_db.return_value.__enter__.return_value = mock_db_session
                
                # Ожидаем, что будет выброшено исключение
                with pytest.raises(Exception, match="DB Error"):
                    get_or_create_user(mock_update, mock_context)

    def test_get_or_create_user_creation_error(self, mock_update, mock_context, mock_db_session):
        """Тест обработки ошибки при создании пользователя."""
        # Имитируем отсутствие пользователя в базе, но ошибка при создании
        with patch('services.user_service.get_user', return_value=None), \
             patch('services.user_service.create_user', side_effect=Exception("Creation Error")):
            
            with patch('services.user_service.get_db') as mock_get_db:
                mock_get_db.return_value.__enter__.return_value = mock_db_session
                
                # Ожидаем, что будет выброшено исключение
                with pytest.raises(Exception, match="Creation Error"):
                    get_or_create_user(mock_update, mock_context)