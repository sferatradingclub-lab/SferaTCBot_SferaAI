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
from handlers import admin_handlers


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


@pytest.mark.anyio
async def test_support_from_dm_button_triggers_handler(monkeypatch):
    monkeypatch.setattr(admin_handlers, "get_db", lambda: DummyDBContext())

    context = SimpleNamespace(
        user_data={
            "admin_state": "users_awaiting_dm",
            "dm_target_user_id": 999,
        },
        bot=SimpleNamespace(send_message=AsyncMock()),
    )

    admin_message = SimpleNamespace(text="Ответ пользователю", reply_text=AsyncMock())
    update = SimpleNamespace(message=admin_message)

    await admin_handlers.handle_admin_message(update, context)

    assert context.user_data.get("admin_state") is None
    context.bot.send_message.assert_awaited_once()
    _, kwargs = context.bot.send_message.await_args
    markup = kwargs.get("reply_markup")
    assert markup is not None
    button = markup.inline_keyboard[0][0]
    assert button.text == "✍️ Ответить"
    assert button.callback_data == "support_from_dm"

    callback_query = SimpleNamespace(
        data="support_from_dm",
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
        message=SimpleNamespace(reply_text=AsyncMock()),
    )
    callback_update = SimpleNamespace(callback_query=callback_query)
    support_context = SimpleNamespace(user_data={}, bot=None)

    await verification_handlers.support_dm_handler(callback_update, support_context)

    assert support_context.user_data.get("state") == "awaiting_support_message"
    callback_query.answer.assert_awaited_once()
    callback_query.edit_message_text.assert_awaited_once()


@pytest.mark.anyio
async def test_admin_reply_sent_with_original_message_reference(monkeypatch):
    monkeypatch.setattr(admin_handlers, "get_db", lambda: DummyDBContext())

    context = SimpleNamespace(
        user_data={
            "admin_state": "users_awaiting_dm",
            "dm_target_user_id": 555,
            "reply_to_message_id": 777,
        },
        bot=SimpleNamespace(send_message=AsyncMock()),
    )

    admin_message = SimpleNamespace(text="Ответ пользователю", reply_text=AsyncMock())
    update = SimpleNamespace(message=admin_message)

    await admin_handlers.handle_admin_message(update, context)

    assert context.user_data.get("admin_state") is None
    assert "reply_to_message_id" not in context.user_data

    context.bot.send_message.assert_awaited_once()
    _, kwargs = context.bot.send_message.await_args
    assert kwargs.get("reply_to_message_id") == 777
    admin_message.reply_text.assert_awaited_once_with("✅ Сообщение успешно отправлено!")
