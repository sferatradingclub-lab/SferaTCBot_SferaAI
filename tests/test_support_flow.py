import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("TELEGRAM_TOKEN", "test-token")
os.environ.setdefault("ADMIN_CHAT_ID", "123456")

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from handlers import common_handlers
from handlers import verification_handlers


class DummyDBContext:
    def __enter__(self):
        return SimpleNamespace()

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_support_messages_override_verification(monkeypatch):
    db_user = SimpleNamespace(awaiting_verification=True, is_banned=False, username="tester")

    monkeypatch.setattr(common_handlers, "get_db", lambda: DummyDBContext())
    monkeypatch.setattr(verification_handlers, "get_db", lambda: DummyDBContext())
    monkeypatch.setattr(common_handlers, "get_user", lambda db, user_id: db_user)
    monkeypatch.setattr(common_handlers, "create_user", lambda db, data: db_user)
    monkeypatch.setattr(common_handlers, "update_user_last_seen", lambda db, user_id: None)
    monkeypatch.setattr(verification_handlers, "get_user", lambda db, user_id: db_user)

    handle_id_mock = AsyncMock()
    monkeypatch.setattr(common_handlers, "handle_id_submission", handle_id_mock)

    support_calls = []

    async def support_wrapper(update, context):
        support_calls.append(update.message.text)
        await verification_handlers.handle_support_message(update, context)

    monkeypatch.setattr(common_handlers, "handle_support_message", support_wrapper)

    user = SimpleNamespace(id=111, full_name="Test User", username="tester")
    context = SimpleNamespace(
        user_data={"state": "awaiting_support_message"},
        bot_data={},
        bot=SimpleNamespace(
            copy_message=AsyncMock(return_value=SimpleNamespace(message_id=555)),
            send_message=AsyncMock()
        ),
        args=[]
    )

    first_message = SimpleNamespace(
        text="Первый вопрос",
        message_id=10,
        reply_text=AsyncMock()
    )
    update = SimpleNamespace(message=first_message, effective_user=user)
    await common_handlers.handle_message(update, context)

    assert context.user_data.get("state") == "awaiting_support_message"

    second_message = SimpleNamespace(
        text="Еще вопрос",
        message_id=11,
        reply_text=AsyncMock()
    )
    update = SimpleNamespace(message=second_message, effective_user=user)
    await common_handlers.handle_message(update, context)

    assert context.user_data.get("state") == "awaiting_support_message"
    assert support_calls == ["Первый вопрос", "Еще вопрос"]
    handle_id_mock.assert_not_called()
    assert context.bot.copy_message.await_count == 2
