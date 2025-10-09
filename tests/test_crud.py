import os
import sys
from pathlib import Path
import pytest
from datetime import datetime, date
from unittest.mock import MagicMock

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
from models.crud import (
    approve_user_in_db,
    reject_user_in_db,
    ban_user_in_db,
    count_total_users,
    count_approved_users,
    count_awaiting_verification_users,
    count_new_users_on_date,
    count_active_users_on_date,
    count_approved_users_on_date,
)


@pytest.fixture
def mock_db_session():
    session = MagicMock()
    query = MagicMock()
    filtered_query = MagicMock()
    filtered_query.update.return_value = 1
    query.filter.return_value = filtered_query
    session.query.return_value = query
    return session


def test_approve_user(mock_db_session):
    """Функция approve_user_in_db должна выполнять атомарное обновление."""
    result = approve_user_in_db(mock_db_session, 12345)

    filtered_query = mock_db_session.query.return_value.filter.return_value
    filtered_query.update.assert_called_once()
    update_payload = filtered_query.update.call_args.kwargs.get("values")
    if update_payload is None:
        update_payload = filtered_query.update.call_args.args[0]

    assert update_payload[User.is_approved] is True
    assert update_payload[User.awaiting_verification] is False
    assert isinstance(update_payload[User.approval_date], datetime)
    mock_db_session.commit.assert_called_once()
    assert result is True


def test_reject_user(mock_db_session):
    """Функция reject_user_in_db должна снимать флаг ожидания."""
    result = reject_user_in_db(mock_db_session, 98765)

    filtered_query = mock_db_session.query.return_value.filter.return_value
    filtered_query.update.assert_called_once_with(
        {User.awaiting_verification: False},
        synchronize_session=False,
    )
    mock_db_session.commit.assert_called_once()
    assert result is True


def test_ban_user(mock_db_session):
    """Функция ban_user_in_db должна корректно блокировать и разблокировать пользователя."""
    ban_user_in_db(mock_db_session, 111, ban_status=True)
    ban_user_in_db(mock_db_session, 111, ban_status=False)

    filtered_query = mock_db_session.query.return_value.filter.return_value
    assert filtered_query.update.call_count == 2
    first_call = filtered_query.update.call_args_list[0]
    second_call = filtered_query.update.call_args_list[1]

    assert first_call.kwargs.get("values", first_call.args[0]) == {User.is_banned: True}
    assert second_call.kwargs.get("values", second_call.args[0]) == {User.is_banned: False}
    assert mock_db_session.commit.call_count == 2


def _prepare_count_session(expected_value=0):
    session = MagicMock()
    query = MagicMock()
    query.filter.return_value = query
    query.select_from.return_value = query
    query.scalar.return_value = expected_value
    query.all.side_effect = AssertionError(".all() should not be used for counting")
    session.query.return_value = query
    return session, query


def test_count_total_users_uses_scalar():
    session, query = _prepare_count_session(expected_value=5)
    assert count_total_users(session) == 5
    session.query.assert_called_once()
    query.scalar.assert_called_once()


def test_count_awaiting_verification_users_filters_properly():
    session, query = _prepare_count_session(expected_value=3)
    assert count_awaiting_verification_users(session) == 3
    query.filter.assert_called_once()
    query.scalar.assert_called_once()


def test_count_approved_users_on_date_avoids_full_read():
    session, query = _prepare_count_session(expected_value=2)
    target = date(2024, 1, 2)
    assert count_approved_users_on_date(session, target) == 2
    query.filter.assert_called_once()
    query.scalar.assert_called_once()


def test_count_approved_users_filters_boolean():
    session, query = _prepare_count_session(expected_value=6)
    assert count_approved_users(session) == 6
    query.filter.assert_called_once()
    query.scalar.assert_called_once()


def test_count_new_and_active_users_on_date_share_infrastructure():
    session, query = _prepare_count_session(expected_value=4)
    target = date(2024, 1, 3)
    assert count_new_users_on_date(session, target) == 4
    session.query.assert_called_once()
    query.scalar.assert_called_once()

    # reset and test active users
    session, query = _prepare_count_session(expected_value=7)
    assert count_active_users_on_date(session, target) == 7
    session.query.assert_called_once()
    query.scalar.assert_called_once()
