import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from handlers.states import UserState
from handlers.user import chatgpt_handler as chatgpt


@pytest.fixture(scope="module")
def anyio_backend():  # type: ignore[override]
    return "asyncio"


@pytest.mark.anyio
async def test_streaming_handler_batches_edits(monkeypatch):
    chunks = ["Привет", " мир", " как", " твои", " дела", " сегодня", "?"]

    async def fake_get_chatgpt_response(history, application):
        # Эмулируем постепенную выдачу ответа, как в реальном стриминге
        for piece in chunks:
            await asyncio.sleep(0.01)
            yield piece

    monkeypatch.setattr(chatgpt, "get_chatgpt_response", fake_get_chatgpt_response)

    keyboard_sentinel = object()
    monkeypatch.setattr(chatgpt, "get_chatgpt_keyboard", lambda: keyboard_sentinel)

    time_values = iter([0.0, 0.3, 0.6, 2.2, 2.4, 2.7, 4.5])

    def time_side_effect():
        try:
            return next(time_values)
        except StopIteration:
            return 4.5

    time_mock = MagicMock(side_effect=time_side_effect)
    monkeypatch.setattr(time, "time", time_mock)
    monkeypatch.setattr(chatgpt.time, "time", time_mock)

    original_set_user_state = chatgpt.StateManager.set_user_state
    state_transitions = []

    def tracking_set_user_state(self, state):
        state_transitions.append(state)
        original_set_user_state(self, state)

    monkeypatch.setattr(chatgpt.StateManager, "set_user_state", tracking_set_user_state)

    placeholder_message = SimpleNamespace(chat_id=777, message_id=101)

    message = SimpleNamespace(
        text="Расскажи интересную историю",
        reply_text=AsyncMock(return_value=placeholder_message),
    )

    created_tasks: list[asyncio.Task] = []

    class DummyApplication:
        def create_task(self, coro, *, name=None):
            task = asyncio.create_task(coro, name=name)
            created_tasks.append(task)
            return task

    context = SimpleNamespace(
        user_data={
            "state": UserState.DEFAULT,
            "chat_history": [
                {"role": "system", "content": "base prompt"},
            ],
        },
        bot=SimpleNamespace(edit_message_text=AsyncMock()),
        application=DummyApplication(),
    )

    update = SimpleNamespace(
        message=message,
        effective_chat=SimpleNamespace(id=placeholder_message.chat_id),
        effective_user=SimpleNamespace(id=111),
    )

    await chatgpt.handle_chatgpt_message(update, context)

    assert created_tasks, "Ожидалась задача потоковой генерации"

    await asyncio.gather(*created_tasks)

    full_text = "".join(chunks)

    message.reply_text.assert_awaited_once_with("✍️")

    edit_calls = context.bot.edit_message_text.await_args_list
    assert len(edit_calls) >= 2
    assert len(edit_calls) < len(chunks)

    streaming_calls = edit_calls[:-1]
    final_call = edit_calls[-1]

    assert streaming_calls, "Ожидались промежуточные обновления при потоковой передаче"

    # Проверяем, что промежуточные обновления накапливают текст и помечены индикатором
    cumulative_length = 0
    for call in streaming_calls:
        text = call.kwargs["text"]
        assert text.endswith(" ✍️")
        streamed_text = text[: -len(" ✍️")]
        assert full_text.startswith(streamed_text)
        assert len(streamed_text) > cumulative_length
        cumulative_length = len(streamed_text)
        assert call.kwargs.get("reply_markup") in (None,)

    # Финальное обновление должно содержать полный ответ без индикатора
    assert final_call.kwargs["text"] == full_text
    assert final_call.kwargs["chat_id"] == placeholder_message.chat_id
    assert final_call.kwargs["message_id"] == placeholder_message.message_id
    assert final_call.kwargs["reply_markup"] is None

    assert state_transitions[0] == UserState.CHATGPT_STREAMING
    assert state_transitions[-1] == UserState.CHATGPT_ACTIVE
    assert context.user_data["state"] == UserState.CHATGPT_ACTIVE

    history = context.user_data["chat_history"]
    assert history == [
        {"role": "system", "content": "base prompt"},
        {"role": "user", "content": message.text},
        {"role": "assistant", "content": full_text},
    ]


@pytest.mark.anyio
async def test_stop_button_interrupts_stream(monkeypatch):
    cancellation_detected = {"triggered": False}

    async def fake_stream(history, application):
        try:
            while True:
                await asyncio.sleep(0.01)
                yield "часть ответа"
        finally:
            cancellation_detected["triggered"] = True

    monkeypatch.setattr(chatgpt, "get_chatgpt_response", fake_stream)
    monkeypatch.setattr(
        chatgpt, "get_main_menu_keyboard", lambda user_id: "main_menu_keyboard"
    )

    placeholder_message = SimpleNamespace(chat_id=555, message_id=999)
    message = SimpleNamespace(
        text="Расскажи что-нибудь",
        reply_text=AsyncMock(return_value=placeholder_message),
    )

    bot = SimpleNamespace(edit_message_text=AsyncMock())
    created_tasks: list[asyncio.Task] = []

    class DummyApplication:
        def create_task(self, coro, *, name=None):
            task = asyncio.create_task(coro, name=name)
            created_tasks.append(task)
            return task

    context = SimpleNamespace(
        user_data={
            "state": UserState.CHATGPT_ACTIVE,
            "chat_history": [
                {"role": "system", "content": chatgpt.CHATGPT_SYSTEM_PROMPT},
            ],
        },
        bot=bot,
        application=DummyApplication(),
    )

    update = SimpleNamespace(
        message=message,
        effective_chat=SimpleNamespace(id=placeholder_message.chat_id),
        effective_user=SimpleNamespace(id=321),
    )

    await chatgpt.handle_chatgpt_message(update, context)

    for _ in range(20):
        if created_tasks:
            break
        await asyncio.sleep(0.01)

    assert created_tasks, "Стрим не успел запуститься"

    await asyncio.sleep(0.05)

    stop_message = SimpleNamespace(reply_text=AsyncMock())
    stop_update = SimpleNamespace(
        message=stop_message,
        effective_user=SimpleNamespace(id=321),
    )

    await chatgpt.perform_chatgpt_stop(stop_update, context)

    if created_tasks:
        await asyncio.gather(*created_tasks, return_exceptions=True)

    assert cancellation_detected["triggered"], "Ожидалось завершение генератора при остановке"

    assert (
        bot.edit_message_text.await_args_list[-1].kwargs["text"]
        == chatgpt.CHATGPT_CANCELLED_MESSAGE
    )

    stop_message.reply_text.assert_awaited_once()
    args, kwargs = stop_message.reply_text.await_args
    assert "Диалог завершен" in args[0]
    assert kwargs["reply_markup"] == "main_menu_keyboard"

    assert "chat_history" not in context.user_data
    assert context.user_data.get("state") == UserState.DEFAULT

    assert "_chatgpt_streaming_sessions" not in context.user_data
