import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


def test_username_lookup_avoids_full_list(monkeypatch):
    from handlers import admin_handlers as ah

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
    context = SimpleNamespace(user_data={'admin_state': 'users_awaiting_id'})

    async def run_test():
        await ah.handle_admin_message(update, context)

    asyncio.run(run_test())

    get_user_by_username.assert_called_once_with(db, "testuser")
    display_user_card.assert_awaited_once_with(update, context, 123)
    assert context.user_data['admin_state'] is None
