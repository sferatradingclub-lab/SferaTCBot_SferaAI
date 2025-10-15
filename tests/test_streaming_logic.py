import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from handlers import common_handlers as ch
from handlers.states import UserState


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

    monkeypatch.setattr(ch, "get_chatgpt_response", fake_get_chatgpt_response)

    keyboard_sentinel = object()
    monkeypatch.setattr(ch, "get_chatgpt_keyboard", lambda: keyboard_sentinel)

    time_values = iter([0.0, 0.3, 0.6, 2.2, 2.4, 2.7, 4.5])

    def time_side_effect():
        try:
            return next(time_values)
        except StopIteration:
            return 4.5

    time_mock = MagicMock(side_effect=time_side_effect)
    monkeypatch.setattr(time, "time", time_mock)
    monkeypatch.setattr(ch.time, "time", time_mock)

    original_set_user_state = ch._set_user_state
    state_transitions = []

    def tracking_set_user_state(context, state):
        state_transitions.append(state)
        original_set_user_state(context, state)

    monkeypatch.setattr(ch, "_set_user_state", tracking_set_user_state)

    placeholder_message = SimpleNamespace(chat_id=777, message_id=101)

    message = SimpleNamespace(
        text="Расскажи интересную историю",
        reply_text=AsyncMock(return_value=placeholder_message),
    )

    context = SimpleNamespace(
        user_data={
            "state": UserState.DEFAULT,
            "chat_history": [
                {"role": "system", "content": "base prompt"},
            ],
        },
        bot=SimpleNamespace(edit_message_text=AsyncMock()),
        application=SimpleNamespace(),
    )

    update = SimpleNamespace(
        message=message,
        effective_chat=SimpleNamespace(id=placeholder_message.chat_id),
    )

    await ch._handle_chatgpt_message(update, context)

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

    # Финальное обновление должно содержать полный ответ без индикатора и корректную клавиатуру
    assert final_call.kwargs["text"] == full_text
    assert final_call.kwargs["chat_id"] == placeholder_message.chat_id
    assert final_call.kwargs["message_id"] == placeholder_message.message_id
    assert final_call.kwargs["reply_markup"] is keyboard_sentinel

    assert state_transitions[0] == UserState.CHATGPT_STREAMING
    assert state_transitions[-1] == UserState.DEFAULT
    assert context.user_data["state"] == UserState.DEFAULT

    history = context.user_data["chat_history"]
    assert history == [
        {"role": "system", "content": "base prompt"},
        {"role": "user", "content": message.text},
        {"role": "assistant", "content": full_text},
    ]
