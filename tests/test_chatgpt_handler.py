import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

from handlers import decorators as handler_decorators
from handlers.states import UserState

import pytest


def test_handle_message_prompts_for_text_when_missing(monkeypatch):
    from handlers import common_handlers as ch

    keyboard = object()

    @contextmanager
    def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(handler_decorators, "get_db", fake_get_db)
    monkeypatch.setattr(
        handler_decorators,
        "get_user",
        lambda db, user_id: SimpleNamespace(is_banned=False, awaiting_verification=False),
    )
    monkeypatch.setattr(handler_decorators, "create_user", lambda db, data: data)
    monkeypatch.setattr(handler_decorators, "update_user_last_seen", lambda db, user_id: None)
    monkeypatch.setattr(ch, "get_chatgpt_keyboard", lambda: keyboard)

    prompt_text = "Пожалуйста, отправьте текстовое сообщение."

    async def run_test():
        user = SimpleNamespace(id=1, full_name="Tester", username="tester")
        message = SimpleNamespace(text=None, reply_text=AsyncMock())
        initial_history = [{"role": "system", "content": "context"}]
        context = SimpleNamespace(
            user_data={
                "state": UserState.CHATGPT_ACTIVE,
                "chat_history": initial_history.copy(),
            },
            bot=SimpleNamespace(send_message=AsyncMock()),
        )
        update = SimpleNamespace(
            effective_user=user,
            message=message,
            effective_chat=SimpleNamespace(id=999),
        )

        await ch.handle_message(update, context)

        assert message.reply_text.await_count == 0
        context.bot.send_message.assert_awaited_once_with(
            chat_id=update.effective_chat.id,
            text=prompt_text,
            reply_markup=keyboard,
        )
        assert context.user_data["chat_history"] == initial_history
        assert all(entry.get("content") is not None for entry in context.user_data["chat_history"])

    asyncio.run(run_test())


def test_chat_history_preserves_order_with_concurrent_messages(monkeypatch):
    from handlers import common_handlers as ch

    keyboard = object()
    monkeypatch.setattr(ch, "get_chatgpt_keyboard", lambda: keyboard)

    call_histories = []
    pending_futures = []

    async def fake_get_chatgpt_response(history, application):
        call_histories.append(list(history))
        future = asyncio.get_running_loop().create_future()
        pending_futures.append(future)
        return await future

    monkeypatch.setattr(ch, "get_chatgpt_response", fake_get_chatgpt_response)

    async def run_test():
        context = SimpleNamespace(
            user_data={
                "chat_history": [
                    {"role": "system", "content": ch.CHATGPT_SYSTEM_PROMPT}
                ]
            },
            application=SimpleNamespace(),
        )

        message1 = SimpleNamespace(
            text="Первый запрос",
            message_id=101,
            reply_text=AsyncMock(),
        )
        update1 = SimpleNamespace(
            message=message1,
            effective_chat=SimpleNamespace(id=1),
        )

        message2 = SimpleNamespace(
            text="Второй запрос",
            message_id=102,
            reply_text=AsyncMock(),
        )
        update2 = SimpleNamespace(
            message=message2,
            effective_chat=SimpleNamespace(id=1),
        )

        task1 = asyncio.create_task(ch._handle_chatgpt_message(update1, context))
        await asyncio.sleep(0)

        assert len(pending_futures) == 1
        assert call_histories[0] == [
            {"role": "system", "content": ch.CHATGPT_SYSTEM_PROMPT},
            {"role": "user", "content": "Первый запрос"},
        ]

        task2 = asyncio.create_task(ch._handle_chatgpt_message(update2, context))
        await asyncio.sleep(0)

        assert len(pending_futures) == 2
        assert call_histories[1] == [
            {"role": "system", "content": ch.CHATGPT_SYSTEM_PROMPT},
            {"role": "user", "content": "Первый запрос"},
            {"role": "user", "content": "Второй запрос"},
        ]

        pending_futures[0].set_result("Ответ на первый")
        await asyncio.sleep(0)

        pending_futures[1].set_result("Ответ на второй")
        await asyncio.gather(task1, task2)

        history = context.user_data["chat_history"]

        assert history == [
            {"role": "system", "content": ch.CHATGPT_SYSTEM_PROMPT},
            {"role": "user", "content": "Первый запрос"},
            {"role": "user", "content": "Второй запрос"},
            {"role": "assistant", "content": "Ответ на первый"},
            {"role": "assistant", "content": "Ответ на второй"},
        ]

        message1.reply_text.assert_awaited_once_with(
            "Ответ на первый",
            reply_markup=keyboard,
        )
        message2.reply_text.assert_awaited_once_with(
            "Ответ на второй",
            reply_markup=keyboard,
        )

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
        monkeypatch.setattr(handler_decorators, "get_db", fake_get_db)
        monkeypatch.setattr(
            handler_decorators,
            "get_user",
            lambda db, user_id: SimpleNamespace(is_banned=False, awaiting_verification=False),
        )
        monkeypatch.setattr(handler_decorators, "create_user", lambda db, data: data)
        monkeypatch.setattr(handler_decorators, "update_user_last_seen", lambda db, user_id: None)
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
            user_data={
                "state": UserState.DEFAULT,
                "chat_history": [{"role": "system", "content": "context"}],
            },
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
