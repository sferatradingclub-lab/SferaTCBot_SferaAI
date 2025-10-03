import os
import sys
from pathlib import Path
import pytest
from datetime import datetime
from unittest.mock import MagicMock, PropertyMock

# Устанавливаем фиктивные переменные окружения до импорта модулей,
# которые обращаются к config.py
os.environ.setdefault("TELEGRAM_TOKEN", "test-token")
os.environ.setdefault("ADMIN_CHAT_ID", "123456")

# Убеждаемся, что корень проекта находится в PYTHONPATH при запуске тестов
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Импортируем тестируемые функции и класс User
from models.user import User
from models.crud import approve_user_in_db, reject_user_in_db, ban_user_in_db

# Фикстура для создания "чистого" объекта пользователя перед каждым тестом
@pytest.fixture
def sample_user():
    user = User()
    user.user_id = 12345
    user.is_approved = False
    user.awaiting_verification = True
    user.approval_date = None
    user.is_banned = False
    return user

# Фикстура для мокирования сессии БД
@pytest.fixture
def mock_db_session(sample_user):
    # Создаем мок сессии
    mock_session = MagicMock()
    
    # Настраиваем метод query().filter().first() так, чтобы он возвращал нашего пользователя
    mock_session.query.return_value.filter.return_value.first.return_value = sample_user
    
    return mock_session

def test_approve_user(mock_db_session, sample_user):
    """
    Тест: функция approve_user_in_db должна:
    1. Установить is_approved в True.
    2. Установить awaiting_verification в False.
    3. Записать текущую дату в approval_date.
    """
    # Вызываем тестируемую функцию
    approve_user_in_db(mock_db_session, sample_user.user_id)
    
    # Проверяем, что состояние пользователя изменилось как ожидалось
    assert sample_user.is_approved is True
    assert sample_user.awaiting_verification is False
    assert sample_user.approval_date is not None
    assert isinstance(sample_user.approval_date, datetime)
    
    # Проверяем, что сессия была закоммичена
    mock_db_session.commit.assert_called_once()

def test_reject_user(mock_db_session, sample_user):
    """
    Тест: функция reject_user_in_db должна:
    1. Установить awaiting_verification в False.
    2. Не изменять is_approved и approval_date.
    """
    # Вызываем тестируемую функцию
    reject_user_in_db(mock_db_session, sample_user.user_id)
    
    # Проверяем, что состояние пользователя изменилось как ожидалось
    assert sample_user.awaiting_verification is False
    assert sample_user.is_approved is False
    assert sample_user.approval_date is None
    
    # Проверяем, что сессия была закоммичена
    mock_db_session.commit.assert_called_once()

def test_ban_user(mock_db_session, sample_user):
    """
    Тест: функция ban_user_in_db должна корректно блокировать пользователя.
    """
    # Блокируем
    ban_user_in_db(mock_db_session, sample_user.user_id, ban_status=True)
    assert sample_user.is_banned is True
    
    # Разблокируем
    ban_user_in_db(mock_db_session, sample_user.user_id, ban_status=False)
    assert sample_user.is_banned is False
    
    # Проверяем, что commit был вызван дважды
    assert mock_db_session.commit.call_count == 2