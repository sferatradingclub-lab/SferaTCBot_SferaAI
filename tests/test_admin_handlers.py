import os
import asyncio
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


os.environ.setdefault("TELEGRAM_TOKEN", "test-token")
os.environ.setdefault("ADMIN_CHAT_ID", "123456")

from handlers import admin_handlers as ah
from handlers.states import AdminState


def test_username_lookup_avoids_full_list(monkeypatch):

    db = SimpleNamespace()

    @contextmanager
    def fake_get_db():
        yield db

    display_user_card = AsyncMock()
    get_user_by_username = MagicMock(return_value=SimpleNamespace(user_id=123, username="testuser"))
    get_all_users = MagicMock(side_effect=AssertionError("get_all_users should not be called"))

    monkeypatch.setattr(ah, "get_db", fake_get_db)
    monkeypatch.setattr(ah, "display_user_card", display_user_card)
    monkeypatch.setattr(ah, "get_user_by_username", get_user_by_username)
    monkeypatch.setattr(ah, "get_all_users", get_all_users)

    update = SimpleNamespace(
        message=SimpleNamespace(text="@TestUser", reply_text=AsyncMock()),
    )
    context = SimpleNamespace(user_data={'admin_state': AdminState.USERS_AWAITING_ID})

    async def run_test():
        await ah.handle_admin_message(update, context)

    asyncio.run(run_test())

    get_user_by_username.assert_called_once_with(db, "testuser")
    display_user_card.assert_awaited_once_with(update, context, 123)
    assert context.user_data['admin_state'] == AdminState.DEFAULT


class _FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        fixed = datetime(2023, 9, 1, 12, 0, 0)
        if tz:
            return fixed.replace(tzinfo=tz)
        return fixed


def _make_admin_update():
    admin_id = int(os.environ["ADMIN_CHAT_ID"])
    return SimpleNamespace(effective_user=SimpleNamespace(id=admin_id))


def test_show_stats_today_uses_aggregators(monkeypatch):

    db = SimpleNamespace()

    @contextmanager
    def fake_get_db():
        yield db

    query = SimpleNamespace(edit_message_text=AsyncMock())
    context = SimpleNamespace()
    update = _make_admin_update()

    mocks = {
        "count_new_users_on_date": MagicMock(return_value=5),
        "count_approved_users_on_date": MagicMock(return_value=3),
        "count_active_users_on_date": MagicMock(return_value=7),
        "count_awaiting_verification_users": MagicMock(return_value=2),
        "get_all_users": MagicMock(side_effect=AssertionError("get_all_users should not be used")),
    }

    monkeypatch.setattr(ah, "get_db", fake_get_db)
    for name, mock in mocks.items():
        monkeypatch.setattr(ah, name, mock)

    monkeypatch.setattr(ah, "datetime", _FixedDatetime)

    async def run_test():
        await ah.show_stats(update, context, query=query, period="today")

    asyncio.run(run_test())

    expected_date = _FixedDatetime.now().date()
    mocks["count_new_users_on_date"].assert_called_once_with(db, expected_date)
    mocks["count_approved_users_on_date"].assert_called_once_with(db, expected_date)
    mocks["count_active_users_on_date"].assert_called_once_with(db, expected_date)
    mocks["count_awaiting_verification_users"].assert_called_once_with(db)

    call = query.edit_message_text.await_args
    assert "Новых: *5*" in call.args[0]
    assert call.kwargs["parse_mode"] == 'MarkdownV2'


def test_show_stats_all_time_uses_aggregators(monkeypatch):

    db = SimpleNamespace()

    @contextmanager
    def fake_get_db():
        yield db

    query = SimpleNamespace(edit_message_text=AsyncMock())
    context = SimpleNamespace()
    update = _make_admin_update()

    mocks = {
        "count_total_users": MagicMock(return_value=10),
        "count_approved_users": MagicMock(return_value=6),
        "count_awaiting_verification_users": MagicMock(return_value=1),
        "get_all_users": MagicMock(side_effect=AssertionError("get_all_users should not be used")),
    }

    monkeypatch.setattr(ah, "get_db", fake_get_db)
    for name, mock in mocks.items():
        monkeypatch.setattr(ah, name, mock)

    monkeypatch.setattr(ah, "datetime", _FixedDatetime)

    async def run_test():
        await ah.show_stats(update, context, query=query, period="all")

    asyncio.run(run_test())

    mocks["count_total_users"].assert_called_once_with(db)
    mocks["count_approved_users"].assert_called_once_with(db)
    mocks["count_awaiting_verification_users"].assert_called_once_with(db)

    call = query.edit_message_text.await_args
    assert "Всего: *10*" in call.args[0]
    assert call.kwargs["parse_mode"] == 'MarkdownV2'


def test_daily_stats_job_uses_aggregators(monkeypatch):

    db = SimpleNamespace()

    @contextmanager
    def fake_get_db():
        yield db

    context = SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))

    mocks = {
        "count_new_users_on_date": MagicMock(return_value=4),
        "count_approved_users_on_date": MagicMock(return_value=2),
        "get_all_users": MagicMock(side_effect=AssertionError("get_all_users should not be used")),
    }

    monkeypatch.setattr(ah, "get_db", fake_get_db)
    for name, mock in mocks.items():
        monkeypatch.setattr(ah, name, mock)

    monkeypatch.setattr(ah, "datetime", _FixedDatetime)

    async def run_test():
        await ah.daily_stats_job(context)

    asyncio.run(run_test())

    expected_date = (_FixedDatetime.now() - ah.timedelta(days=1)).date()
    mocks["count_new_users_on_date"].assert_called_once_with(db, expected_date)
    mocks["count_approved_users_on_date"].assert_called_once_with(db, expected_date)
    call = context.bot.send_message.await_args
    assert "Новых: *4*" in call.kwargs["text"]
    assert call.kwargs["parse_mode"] == 'MarkdownV2'
