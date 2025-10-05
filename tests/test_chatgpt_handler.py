import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


def test_handle_message_prompts_for_text_when_missing(monkeypatch):
    from handlers import common_handlers as ch

    keyboard = object()

    @contextmanager
    def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(ch, "get_db", fake_get_db)
    monkeypatch.setattr(
        ch,
        "get_user",
        lambda db, user_id: SimpleNamespace(is_banned=False, awaiting_verification=False),
    )
    monkeypatch.setattr(ch, "create_user", lambda db, data: data)
    monkeypatch.setattr(ch, "update_user_last_seen", lambda db, user_id: None)
    monkeypatch.setattr(ch, "get_chatgpt_keyboard", lambda: keyboard)

    prompt_text = (
        "Пожалуйста, отправьте текстовое сообщение для ИИ-ассистента "
        "или завершите диалог с помощью кнопки ниже."
    )

    async def run_test():
        user = SimpleNamespace(id=1, full_name="Tester", username="tester")
        message = SimpleNamespace(text=None, reply_text=AsyncMock())
        initial_history = [{"role": "system", "content": "context"}]
        context = SimpleNamespace(
            user_data={"state": "chatgpt_active", "chat_history": initial_history.copy()},
            bot=SimpleNamespace(send_message=AsyncMock()),
        )
        update = SimpleNamespace(
            effective_user=user,
            message=message,
            effective_chat=SimpleNamespace(id=999),
        )

        await ch.handle_message(update, context)

        message.reply_text.assert_awaited_once()
        awaited_call = message.reply_text.await_args
        assert awaited_call.args == (prompt_text,)
        assert awaited_call.kwargs == {"reply_markup": keyboard}
        assert context.user_data["chat_history"] == initial_history
        assert all(entry.get("content") is not None for entry in context.user_data["chat_history"])

    asyncio.run(run_test())


@pytest.mark.parametrize("has_message", [True, False])
def test_handle_message_sends_main_menu_reminder_when_inactive(monkeypatch, has_message):
    from handlers import common_handlers as ch

    reminder_keyboard = object()
    keyboard_calls = []

    @contextmanager
    def fake_get_db():
        yield SimpleNamespace()

    def fake_get_main_menu_keyboard(user_id):
        keyboard_calls.append(user_id)
        return reminder_keyboard

    async def run_test():
        monkeypatch.setattr(ch, "get_db", fake_get_db)
        monkeypatch.setattr(
            ch,
            "get_user",
            lambda db, user_id: SimpleNamespace(is_banned=False, awaiting_verification=False),
        )
        monkeypatch.setattr(ch, "create_user", lambda db, data: data)
        monkeypatch.setattr(ch, "update_user_last_seen", lambda db, user_id: None)
        monkeypatch.setattr(ch, "get_main_menu_keyboard", fake_get_main_menu_keyboard)

        user = SimpleNamespace(id=42, full_name="Inactive User", username="inactive")
        message = None
        if has_message:
            message = SimpleNamespace(reply_text=AsyncMock())

        effective_chat = SimpleNamespace(id=777)
        update = SimpleNamespace(
            effective_user=user,
            message=message,
            effective_chat=effective_chat,
        )
        context = SimpleNamespace(
            user_data={"chat_history": [{"role": "system", "content": "context"}]},
            bot=SimpleNamespace(send_message=AsyncMock()),
        )

        await ch.handle_message(update, context)

        assert keyboard_calls == [user.id]

        if has_message:
            message.reply_text.assert_awaited_once_with(
                ch.FRIENDLY_MAIN_MENU_REMINDER,
                reply_markup=reminder_keyboard,
            )
            assert context.bot.send_message.await_count == 0
        else:
            context.bot.send_message.assert_awaited_once_with(
                chat_id=effective_chat.id,
                text=ch.FRIENDLY_MAIN_MENU_REMINDER,
                reply_markup=reminder_keyboard,
            )

    asyncio.run(run_test())
